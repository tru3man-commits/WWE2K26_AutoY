import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox

from background import BackgroundJob
import autoy
from controller_manager import DATA, Manager, command, discover, run


class Desktop(autoy.AutoY):
    def __init__(self, root):
        self.manager = None
        self.busy = False
        self.close_requested = False
        self.closing_cleanup = False
        super().__init__(root)
        self.configure_btn = tk.Button(root, text='Select controller...', command=self.select_controller)
        self.configure_btn.pack(pady=2)
        self.restore_btn = tk.Button(root, text='Restore controller', command=self.restore_controller)
        self.restore_btn.pack(pady=2)
        tk.Label(root, text='Start AutoY before the game. Stop makes your physical controller available again.',
                 wraplength=550, fg='#555').pack(pady=4)
        root.title('WWE 2K26 AutoY 0.2.2')
        self.start_btn.config(state='disabled')
        root.after(100, self.initialize)

    def run_background(self, label, operation, complete, failed=None):
        if self.busy:
            return
        self.busy = True
        for button in (self.start_btn, self.stop_btn, self.configure_btn, self.restore_btn):
            button.config(state='disabled')
        self.status.set(label)
        job = BackgroundJob()
        started = time.monotonic()
        job.start(operation)
        def poll():
            result = job.poll()
            if result is None:
                self.status.set(label + f" ({int(time.monotonic() - started)} s)")
                self.root.after(100, poll)
                return
            self.busy = False
            self.start_btn.config(state='disabled' if self.running else 'normal')
            self.stop_btn.config(state='normal' if self.running else 'disabled')
            self.configure_btn.config(state='disabled' if self.running else 'normal')
            self.restore_btn.config(state='normal')
            if self.close_requested:
                self.close()
                return
            success, value = result
            if success:
                complete(value)
            else:
                self.status.set('Operation failed - see latest.log')
                if failed:
                    failed(value)
                else:
                    messagebox.showerror('AutoY', str(value))
        self.root.after(50, poll)

    def initialize(self):
        def work():
            self.manager = Manager()
            self.manager.hid.prepare()
            self.manager.stop()
            return self.manager.profile()
        def ready(profile):
            if profile:
                self.status.set('Ready - ' + profile['name'])
            else:
                self.select_controller()
        self.run_background('Checking controller setup...', work, ready)

    def select_controller(self):
        if self.busy or self.running:
            return
        def work():
            if self.manager is None:
                self.manager = Manager()
            self.manager.hid.prepare()
            candidates = discover()
            if not candidates:
                raise RuntimeError('No supported physical Xbox controller found. Connect it via Bluetooth or USB, close other controller emulators, and retry.\nDiagnostics: ' + str(DATA / 'discovery.json'))
            return candidates
        self.run_background('Finding physical Xbox controllers...', work, self.show_controllers)

    def show_controllers(self, candidates):
        self.status.set('Select your physical controller')
        win = tk.Toplevel(self.root)
        win.title('Select your physical Xbox controller')
        win.transient(self.root); win.grab_set()
        tk.Label(win, text='Connect only the Xbox controller you want to use.\nAutoY will hide it while running and unhide it when stopped.').pack(padx=15, pady=12)
        listing = tk.Listbox(win, width=85, height=min(6, len(candidates)))
        listing.pack(padx=15, pady=5)
        for item in candidates:
            listing.insert('end', item['name'] + ' - ' + item['paths'][0])
        listing.selection_set(0)
        def accept():
            selected = listing.curselection()
            if not selected or self.busy:
                return
            candidate = candidates[selected[0]]
            button.config(state='disabled')
            def done(_):
                self.status.set('Ready - controller will be visible whenever AutoY is stopped')
                if win.winfo_exists():
                    win.destroy()
            def error(exc):
                if win.winfo_exists():
                    button.config(state='normal')
                messagebox.showerror('Controller setup', str(exc))
            self.run_background('Saving controller setup...', lambda: self.manager.select(candidate), done, error)
        button = tk.Button(win, text='Use this controller', command=accept)
        button.pack(pady=12)

    def visible_to_games(self):
        if not getattr(sys, 'frozen', False):
            raise RuntimeError('Automatic hiding verification requires the built EXE. Run BUILD_EXE.bat first.')
        probe = Path(sys.executable).with_name('ControllerProbe.exe')
        if not probe.exists():
            raise RuntimeError('ControllerProbe.exe is missing. Keep the whole installed application folder together.')
        return json.loads(run([str(probe), '--probe']))

    def start(self):
        if self.running or self.busy:
            return
        try:
            if not self.manager or not self.manager.profile():
                self.select_controller()
                return
            self.status.set('Preparing controller and recovery watchdog...')
            self.root.update_idletasks()
            self.manager.begin()
            if self.visible_to_games():
                messagebox.showinfo('Reconnect your controller',
                    'Switch your Xbox controller off and on (or unplug and reconnect USB), then click OK.\n\nKeep the game closed until AutoY says Running.')
                if self.visible_to_games():
                    raise RuntimeError('A physical controller is still visible to games. Re-select your controller and connect only one Xbox pad. AutoY has restored normal access.')
            # Original physical-to-virtual button/axis forwarding starts here.
            super().start()
            if not self.running:
                self.manager.stop()
            else:
                self.configure_btn.config(state='disabled')
        except Exception as exc:
            try:
                self.stop()
            except Exception as recovery:
                exc = RuntimeError(str(exc) + '\nRecovery: ' + str(recovery))
            self.status.set('Stopped - controller setup failed')
            messagebox.showerror('AutoY', str(exc))

    def stop(self):
        error = None
        try:
            super().stop()
        except Exception as exc:
            error = exc
        finally:
            if self.manager:
                try:
                    self.manager.stop()
                except Exception as exc:
                    error = RuntimeError(str(error or '') + '\nController recovery: ' + str(exc))
            if hasattr(self, 'configure_btn'):
                self.configure_btn.config(state='normal')
        if error:
            raise error
        self.status.set('Stopped - physical controller restored')

    def restore_controller(self):
        try:
            self.stop()
            messagebox.showinfo('Controller restored', 'Your selected controller is no longer hidden by AutoY.\nIf a game still cannot see it, reconnect the controller and restart the game.')
        except Exception as exc:
            messagebox.showerror('Recovery failed', str(exc))

    def close(self):
        if self.closing_cleanup:
            return
        if self.busy:
            self.close_requested = True
            self.status.set('Finishing the current operation before closing...')
            return
        # Join forwarding workers before touching HidHide, then release the
        # controller in the background so the window can still repaint.
        self.close_requested = False
        self.closing_cleanup = True
        try:
            autoy.AutoY.stop(self)
        except Exception as exc:
            messagebox.showerror('AutoY', str(exc))
        def finish(_):
            self.hotkeys.stop()
            self.root.destroy()
        def failed(exc):
            messagebox.showerror('Controller recovery', str(exc) + '\nRecovery will retry after AutoY exits. You can also use Restore controller from the Start menu.')
            finish(None)
        self.run_background('Restoring controller before closing...',
                            lambda: self.manager.stop() if self.manager else None,
                            finish, failed)
