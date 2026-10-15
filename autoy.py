"""Offline WWE 2K26 Y prompt helper with virtual-pad left/right controls."""
import json
import ctypes
from ctypes import wintypes
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox

import cv2
import numpy as np
import mss
import vgamepad as vg
from pynput import keyboard

CONFIG = "autoy_config.json"
DEFAULT = {
    "roi": [0.0, 0.0, 1.0, 1.0],
    "scan_interval_ms": 0,
    "button_ms": 120,
    "rearm_ms": 120,
}


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [("wButtons", wintypes.WORD), ("bLeftTrigger", ctypes.c_ubyte),
                ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
                ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short),
                ("sThumbRY", ctypes.c_short)]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD)]


class XInput:
    def __init__(self):
        self.dll = ctypes.WinDLL("xinput1_4.dll")
        self.dll.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
        self.dll.XInputGetState.restype = wintypes.DWORD

    def get_state(self, index):
        state = XINPUT_STATE()
        if self.dll.XInputGetState(index, ctypes.byref(state)) != 0:
            return None
        return state

    def first_connected(self):
        return next((i for i in range(4) if self.get_state(i) is not None), None)


class AutoY:
    def __init__(self, root):
        self.root = root
        root.title("WWE 2K26 Auto Y")
        root.resizable(False, False)
        root.geometry("580x440")
        try:
            with open(CONFIG, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Preserve a user's screen area, but replace old OCR-era timing
            # values so an existing config cannot silently restore slow scans.
            for key in ("scan_interval_ms", "button_ms", "rearm_ms",
                        "tesseract_path", "confidence"):
                saved.pop(key, None)
            self.cfg = {**DEFAULT, **saved}
        except (OSError, json.JSONDecodeError):
            self.cfg = DEFAULT.copy()
        self.pad = None
        self.xinput = None
        self.pad_index = None
        self.output_thread = None
        self.scan_thread = None
        self.ui_queue = queue.Queue()
        self.running = False
        self.last_tap = 0.0
        self.auto_y_until = 0.0
        self.state_lock = threading.Lock()
        self.hotkeys = keyboard.GlobalHotKeys({
            "<ctrl>+<alt>+y": lambda: self.tap_y(manual=True) if self.running else None,
        })
        self.hotkeys.start()

        tk.Label(root, text="WWE 2K26 Auto Y", font=("Segoe UI", 16, "bold")).pack(padx=18, pady=(16, 4))
        tk.Label(root, text="Your Xbox controller and Auto Y share one virtual controller", fg="#555").pack(pady=(0, 10))
        self.status = tk.StringVar(value="Stopped")
        tk.Label(root, textvariable=self.status, font=("Segoe UI", 10), wraplength=410).pack(padx=14, pady=4)
        self.input_status = tk.StringVar(value="Controller input: not started")
        tk.Label(root, textvariable=self.input_status, font=("Consolas", 9), wraplength=410,
                 justify="left", anchor="w").pack(fill="x", padx=18, pady=(2, 4))
        bar = tk.Frame(root); bar.pack(pady=8)
        self.start_btn = tk.Button(bar, text="Start", width=11, command=self.start)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = tk.Button(bar, text="Stop", width=11, command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        tk.Label(root, text="Ctrl+Alt+Y: manual Y test\nUltra-fast detection of the yellow circular Y prompt.", fg="#555").pack(padx=18, pady=(8, 5))
        tk.Button(root, text="Screen region...", command=self.set_roi).pack(pady=(2, 14))
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(25, self.drain_ui)

    def drain_ui(self):
        for _ in range(50):
            try:
                callback = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            callback()
        self.root.after(25, self.drain_ui)

    def start(self):
        try:
            self.xinput = XInput()
            connected = [i for i in range(4) if self.xinput.get_state(i) is not None]
            if len(connected) > 1:
                raise RuntimeError("Connect only one physical Xbox controller and close other controller emulators.")
            self.pad_index = connected[0] if connected else None
            if self.pad_index is None:
                raise RuntimeError("No Xbox controller detected. Connect your controller and retry.")
            self.pad = vg.VX360Gamepad()
        except Exception as e:
            messagebox.showerror("Controller error", f"Check your controller connection and the ViGEmBus installation.\n\n{e}")
            return
        self.last_tap = 0.0
        self.auto_y_until = 0.0
        self.running = True
        self.start_btn.config(state="disabled"); self.stop_btn.config(state="normal")
        self.status.set(
            f"Running - physical Xbox controller #{self.pad_index + 1} "
            f"(XInput {self.pad_index}) -> virtual Xbox controller"
        )
        self.input_status.set("Controller input: listening...")
        self.scan_thread = threading.Thread(target=self.scan_loop, daemon=True)
        self.scan_thread.start()
        self.output_thread = threading.Thread(target=self.output_loop, daemon=True)
        self.output_thread.start()

    def stop(self):
        self.running = False
        self.start_btn.config(state="normal"); self.stop_btn.config(state="disabled")
        self.status.set("Stopped")
        self.input_status.set("Controller input: stopped")
        for worker in (self.output_thread, self.scan_thread):
            if worker and worker.is_alive():
                worker.join(timeout=3)
                if worker.is_alive():
                    raise RuntimeError("A worker did not stop. Close AutoY; recovery will restore your controller.")
        while not self.ui_queue.empty():
            try:
                self.ui_queue.get_nowait()
            except queue.Empty:
                break
        if self.pad:
            self.pad.reset(); self.pad.update()
            self.pad = None

    def tap_y(self, manual=False):
        with self.state_lock:
            self.auto_y_until = time.monotonic() + int(self.cfg["button_ms"]) / 1000
        if manual:
            self.ui_queue.put(lambda: self.status.set("Manual Y test sent"))

    def output_loop(self):
        mapping = {
            0x0001: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            0x0002: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            0x0004: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            0x0008: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
            0x0010: vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            0x0020: vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            0x0040: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            0x0080: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
            0x0100: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            0x0200: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            0x1000: vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            0x2000: vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            0x4000: vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            0x8000: vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
        }
        y_button = vg.XUSB_BUTTON.XUSB_GAMEPAD_Y
        button_names = {
            0x0001: "D-pad up", 0x0002: "D-pad down",
            0x0004: "D-pad left", 0x0008: "D-pad right",
            0x0010: "Start", 0x0020: "Back",
            0x0040: "L3", 0x0080: "R3",
            0x0100: "LB", 0x0200: "RB",
            0x1000: "A", 0x2000: "B", 0x4000: "X", 0x8000: "Y",
        }
        last_ui_update = 0.0
        try:
            while self.running:
                state = self.xinput.get_state(self.pad_index)
                if state is None:
                    raise RuntimeError("The physical Xbox controller disconnected.")
                gamepad = state.Gamepad
                physical_buttons = int(gamepad.wButtons)
                now = time.monotonic()
                with self.state_lock:
                    y_on = now < self.auto_y_until
                for mask, button in mapping.items():
                    if physical_buttons & mask or (button == y_button and y_on):
                        self.pad.press_button(button=button)
                    else:
                        self.pad.release_button(button=button)
                self.pad.left_trigger(value=gamepad.bLeftTrigger)
                self.pad.right_trigger(value=gamepad.bRightTrigger)
                self.pad.left_joystick(x_value=gamepad.sThumbLX, y_value=gamepad.sThumbLY)
                self.pad.right_joystick(x_value=gamepad.sThumbRX, y_value=gamepad.sThumbRY)
                self.pad.update()
                if now - last_ui_update >= 0.1:
                    lx = max(-100, min(100, round(gamepad.sThumbLX * 100 / 32767)))
                    ly = max(-100, min(100, round(gamepad.sThumbLY * 100 / 32767)))
                    rx = max(-100, min(100, round(gamepad.sThumbRX * 100 / 32767)))
                    ry = max(-100, min(100, round(gamepad.sThumbRY * 100 / 32767)))
                    active = [name for mask, name in button_names.items() if physical_buttons & mask]
                    if gamepad.bLeftTrigger > 0:
                        active.append(f"LT {round(gamepad.bLeftTrigger * 100 / 255)}%")
                    if gamepad.bRightTrigger > 0:
                        active.append(f"RT {round(gamepad.bRightTrigger * 100 / 255)}%")
                    if y_on:
                        active.append("Auto Y")
                    info = (f"Left stick X:{lx:+d}% Y:{ly:+d}%   "
                            f"Right stick X:{rx:+d}% Y:{ry:+d}%\n"
                            f"Active buttons: {', '.join(active) if active else '—'}")
                    self.ui_queue.put(lambda info=info: self.input_status.set(info))
                    last_ui_update = now
                time.sleep(0.001)
        except Exception as e:
            self.running = False
            msg = str(e)
            self.ui_queue.put(lambda msg=msg: self.fail(msg))

    def scan_loop(self):
        try:
            with mss.mss() as sct:
                prompt_seen = False
                while self.running:
                    started = time.monotonic()
                    mon = sct.monitors[1]
                    x1, y1, x2, y2 = self.cfg["roi"]
                    region = {
                        "left": mon["left"] + int(mon["width"] * x1),
                        "top": mon["top"] + int(mon["height"] * y1),
                        "width": max(1, int(mon["width"] * (x2 - x1))),
                        "height": max(1, int(mon["height"] * (y2 - y1))),
                    }
                    grabbed = sct.grab(region)
                    shot = cv2.cvtColor(np.asarray(grabbed), cv2.COLOR_BGRA2RGB)
                    found = self.find_y_icon(shot)
                    now = time.monotonic()
                    if found and not prompt_seen and now - self.last_tap >= int(self.cfg["rearm_ms"]) / 1000:
                        self.last_tap = now
                        prompt_seen = True
                        self.tap_y()
                        self.ui_queue.put(lambda: self.status.set("Y prompt detected - button sent"))
                    if not found:
                        prompt_seen = False
                    time.sleep(max(0, int(self.cfg["scan_interval_ms"]) / 1000 - (time.monotonic() - started)))
        except Exception as e:
            self.running = False
            msg = str(e)
            self.ui_queue.put(lambda msg=msg: self.fail(msg))

    def find_y_icon(self, image):
        """Fast detection: the WWE Y prompt is a small, saturated yellow circle."""
        rgb = np.asarray(image)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        yellow = cv2.inRange(hsv, np.array((20, 120, 150), dtype=np.uint8),
                             np.array((40, 255, 255), dtype=np.uint8))
        contours, _ = cv2.findContours(yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        height, width = yellow.shape
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if not (18 <= w <= min(140, width) and 18 <= h <= min(140, height)):
                continue
            aspect = w / h
            if not 0.78 <= aspect <= 1.22:
                continue
            perimeter = cv2.arcLength(contour, True)
            area = cv2.contourArea(contour)
            circularity = (4 * np.pi * area / (perimeter * perimeter)) if perimeter else 0
            if circularity < 0.72:
                continue
            # OCR added a large delay to short-lived prompts. The Y cue is
            # uniquely yellow in the tested WWE prompt; circle geometry filters
            # out unrelated yellow text and HUD elements.
            return True
        return False

    def fail(self, msg):
        self.stop()
        self.start_btn.config(state="normal"); self.stop_btn.config(state="disabled")
        self.status.set("Stopped")
        self.input_status.set("Controller input: error - forwarding stopped")
        messagebox.showerror("Auto Y stopped", f"{msg}\n\nCheck the controller connection and the screen region.")

    def set_roi(self):
        win = tk.Toplevel(self.root); win.title("Screen region (fractions of the first monitor)"); win.resizable(False, False)
        entries = []
        for i, label in enumerate(("Left", "Top", "Right", "Bottom")):
            tk.Label(win, text=label).grid(row=i, column=0, padx=10, pady=4, sticky="w")
            ent = tk.Entry(win, width=10); ent.insert(0, str(self.cfg["roi"][i]))
            ent.grid(row=i, column=1, padx=10, pady=4); entries.append(ent)
        tk.Label(win, text="Values from 0 to 1 (0.5 = half the screen)", fg="#555").grid(row=4, column=0, columnspan=2, padx=10, pady=6)
        def save():
            try:
                roi = [float(e.get()) for e in entries]
                if not (0 <= roi[0] < roi[2] <= 1 and 0 <= roi[1] < roi[3] <= 1): raise ValueError()
                self.cfg["roi"] = roi
                with open(CONFIG, "w", encoding="utf-8") as f: json.dump(self.cfg, f, indent=2)
                win.destroy()
            except ValueError:
                messagebox.showerror("Invalid region", "Enter values from 0 to 1. Left/top must be smaller than right/bottom.")
        tk.Button(win, text="Save", command=save).grid(row=5, column=0, columnspan=2, pady=10)

    def close(self):
        self.stop(); self.hotkeys.stop(); self.root.destroy()


if __name__ == "__main__":
    app = tk.Tk(); AutoY(app); app.mainloop()
