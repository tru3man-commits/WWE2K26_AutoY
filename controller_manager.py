"""Own only the selected controller's HidHide entries; journal before changes."""
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

DATA = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'WWE2K26_AutoY'
PROFILE = DATA / 'controller.json'
JOURNAL = DATA / 'controller-session.json'
READY = DATA / 'watchdog-ready.json'


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def command(*args):
    if getattr(sys, 'frozen', False):
        return [sys.executable, *args]
    return [sys.executable, str(Path(__file__).with_name('launcher.py')), *args]


def run(args, timeout=20):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    out = proc.stdout.decode('utf-8-sig', errors='replace')
    err = proc.stderr.decode('utf-8-sig', errors='replace')
    if proc.returncode:
        raise RuntimeError('Command failed. Close HidHide Configuration Client and retry.\n' + (err or out)[-1800:])
    return out


class HidHide:
    def __init__(self):
        for env in ('ProgramW6432', 'ProgramFiles', 'ProgramFiles(x86)'):
            root = Path(os.environ.get(env, 'C:/Program Files')) / 'Nefarius Software Solutions' / 'HidHide'
            for path in (root / 'HidHideCLI.exe', root / 'x64' / 'HidHideCLI.exe'):
                if path.is_file():
                    self.path = path
                    return
        raise RuntimeError('HidHide is not installed. Run the AutoY Setup installer and restart Windows if requested.')

    def call(self, *args):
        return run([str(self.path), *args])

    def hidden(self):
        text = self.call('--dev-list')
        paths = re.findall(r'--dev-hide\s+"([^"]+)"', text)
        if '--dev-hide' in text and len(paths) != text.count('--dev-hide'):
            raise RuntimeError('Cannot read the HidHide device list safely. No device settings were changed.')
        return set(paths)

    def cloak(self):
        value = self.call('--cloak-state').strip()
        if value not in ('--cloak-on', '--cloak-off'):
            raise RuntimeError('Unexpected HidHide cloak status: ' + value)
        return value == '--cloak-on'

    def prepare(self):
        if self.call('--inv-state').strip() != '--inv-off':
            raise RuntimeError('HidHide inverse mode is enabled. AutoY requires normal mode and will not overwrite your profile.')
        self.call('--app-reg', str(Path(sys.executable).resolve()))

    def unhide(self, paths):
        if paths:
            args = [part for path in paths for part in ('--dev-unhide', path)]
            self.call(*args)
        remaining = {p.casefold() for p in self.hidden()}
        if any(p.casefold() in remaining for p in paths):
            raise RuntimeError('The controller is still hidden. Close HidHide Configuration Client, then click Restore controller.')


def restore(hid=None, journal=JOURNAL, token=None):
    if not journal.exists():
        return
    state = read_json(journal)
    if token and state['token'] != token:
        return
    hid = hid or HidHide()
    # Explicitly managed controllers must be usable without AutoY, even if
    # they were hidden by the user's previous manual AutoY configuration.
    hid.unhide(state['devices'])
    remaining = {x.casefold() for x in hid.hidden()}
    before_other = {x.casefold() for x in state['other_before']}
    if not state['cloak_before'] and remaining == before_other:
        hid.call('--cloak-off')
    # Keep the journal until every requested operation has succeeded.
    journal.unlink(missing_ok=True)


class Manager:
    def __init__(self, hid=None, profile=PROFILE, journal=JOURNAL):
        self.hid = hid or HidHide()
        self.profile_path = profile
        self.journal = journal
        self.guard = None

    def profile(self):
        return read_json(self.profile_path) if self.profile_path.exists() else None

    def select(self, candidate):
        if self.journal.exists():
            raise RuntimeError('Stop AutoY before changing the controller.')
        old = self.profile()
        if old:
            self.hid.unhide(old['paths'])
        atomic_json(self.profile_path, candidate)
        self.hid.unhide(candidate['paths'])

    def begin(self, arm=True):
        self.hid.prepare()
        restore(self.hid, self.journal)
        profile = self.profile()
        if not profile:
            raise RuntimeError('Select your controller first.')
        selected = profile['paths']
        hidden = self.hid.hidden()
        chosen = {x.casefold() for x in selected}
        state = dict(token=uuid.uuid4().hex, devices=selected,
                     cloak_before=self.hid.cloak(),
                     other_before=[x for x in hidden if x.casefold() not in chosen])
        atomic_json(self.journal, state)
        try:
            if arm:
                install_login_recovery()
                self.arm_watchdog(state['token'])
            self.hid.call(*[p for d in selected for p in ('--dev-hide', d)], '--cloak-on')
            now = {x.casefold() for x in self.hid.hidden()}
            if not chosen.issubset(now) or not self.hid.cloak():
                raise RuntimeError('HidHide did not accept the controller settings.')
        except Exception:
            restore(self.hid, self.journal)
            raise

    def arm_watchdog(self, token):
        READY.unlink(missing_ok=True)
        self.guard = subprocess.Popen(command('--watch', str(os.getpid()), token),
                                      creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if READY.exists() and read_json(READY).get('token') == token:
                return
            if self.guard.poll() is not None:
                break
            time.sleep(.05)
        raise RuntimeError('The recovery watchdog could not start. The controller was not hidden.')

    def stop(self):
        restore(self.hid, self.journal)
        profile = self.profile()
        if profile:
            self.hid.unhide(profile['paths'])


def install_login_recovery():
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        winreg.SetValueEx(key, 'WWE2K26_AutoY_Recovery', 0, winreg.REG_SZ,
                         subprocess.list2cmdline(command('--recover-only')))


def watch(pid, token):
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        restore(token=token)
        return
    try:
        atomic_json(READY, {'token': token})
        while True:
            try:
                if read_json(JOURNAL)['token'] != token:
                    return
            except FileNotFoundError:
                return
            result = kernel.WaitForSingleObject(handle, 500)
            if result == 0:
                for _ in range(30):
                    try:
                        restore(token=token)
                        return
                    except Exception:
                        time.sleep(1)
                raise RuntimeError('Recovery could not access HidHide. Use Restore controller from the Start menu.')
            if result != 258:
                raise RuntimeError('Could not monitor the AutoY process.')
    finally:
        kernel.CloseHandle(handle)


def discover():
    """Use PnP data, avoiding HidHideCLI's locale-dependent JSON truncation."""
    script = Path(__file__).with_name('discover_controllers.ps1')
    out = run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script)], timeout=45)
    from device_inventory import candidates_from_inventory
    data = json.loads(out or '[]')
    records = data if isinstance(data, list) else [data]
    candidates = candidates_from_inventory(records)
    atomic_json(DATA / 'discovery.json', {'devices': records, 'candidates': candidates})
    print('Controller discovery:', len(records), 'records;', len(candidates), 'candidates', flush=True)
    return candidates
