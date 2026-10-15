"""Windows desktop, watchdog and emergency recovery entry points."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import traceback


def probe():
    class Pad(ctypes.Structure):
        _fields_ = [('buttons', wintypes.WORD), ('lt', ctypes.c_ubyte), ('rt', ctypes.c_ubyte),
                    ('lx', ctypes.c_short), ('ly', ctypes.c_short), ('rx', ctypes.c_short), ('ry', ctypes.c_short)]
    class State(ctypes.Structure):
        _fields_ = [('packet', wintypes.DWORD), ('pad', Pad)]
    dll = ctypes.WinDLL('xinput1_4.dll')
    dll.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(State)]
    dll.XInputGetState.restype = wintypes.DWORD
    # A windowed PyInstaller application has no sys.stdout. Write the JSON
    # directly to the redirected standard-output Windows handle.
    data = json.dumps([i for i in range(4) if dll.XInputGetState(i, ctypes.byref(State())) == 0]).encode()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]; kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    written = wintypes.DWORD()
    if not kernel.WriteFile(kernel.GetStdHandle(-11 & 0xffffffff), data, len(data), ctypes.byref(written), None):
        raise ctypes.WinError(ctypes.get_last_error())


def acquire_lock():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel.CreateMutexW(None, False, 'Local\\WWE2K26AutoY.Managed')
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
        return None
    return handle


def main():
    if '--probe' in sys.argv:
        probe(); return
    from controller_manager import DATA, PROFILE, JOURNAL, Manager, restore, watch
    DATA.mkdir(parents=True, exist_ok=True)
    os.chdir(DATA)
    background = any(flag in sys.argv for flag in ('--watch', '--recover-only', '--restore-silent'))
    logname = 'recovery.log' if background else 'latest.log'
    log = open(DATA / logname, 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log
    try:
        if '--watch' in sys.argv:
            idx = sys.argv.index('--watch')
            watch(int(sys.argv[idx + 1]), sys.argv[idx + 2]); return
        lock = acquire_lock()
        if lock is None:
            if '--restore-silent' in sys.argv:
                raise RuntimeError('Close AutoY before uninstalling.')
            if not background:
                ctypes.windll.user32.MessageBoxW(None, 'AutoY is already running. Use Stop or Restore controller in its window.', 'AutoY', 64)
            return
        # Keep lock alive until process termination. Recovery must not race a session.
        if '--recover-only' in sys.argv:
            restore(); return
        if '--restore' in sys.argv or '--restore-silent' in sys.argv:
            if PROFILE.exists() or JOURNAL.exists():
                Manager().stop()
            if not background:
                ctypes.windll.user32.MessageBoxW(None, 'Controller restored. Reconnect it if needed.', 'AutoY', 64)
            return
        import tkinter as tk
        from desktop import Desktop
        root = tk.Tk()
        def report(kind, value, tb):
            traceback.print_exception(kind, value, tb)
            from tkinter import messagebox
            messagebox.showerror('AutoY', str(value) + '\nLog: ' + str(DATA / logname))
        root.report_callback_exception = report
        Desktop(root)
        root.mainloop()
    except Exception:
        traceback.print_exc()
        if not background:
            ctypes.windll.user32.MessageBoxW(None, 'AutoY could not complete the operation.\n' + traceback.format_exc()[-1500:] + '\nLog: ' + str(DATA / logname), 'AutoY', 16)
        raise


if __name__ == '__main__':
    main()
