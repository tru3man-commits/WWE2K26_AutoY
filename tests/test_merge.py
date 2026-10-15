"""Exercise the real output_loop body without Windows drivers or a GUI."""
import ast
from pathlib import Path
from types import SimpleNamespace
import queue
import threading
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'autoy.py'

class Pad:
    def __init__(self): self.buttons=set(); self.values={}; self.updates=0
    def press_button(self, button): self.buttons.add(button)
    def release_button(self, button): self.buttons.discard(button)
    def left_trigger(self, **kw): self.values['lt']=kw
    def right_trigger(self, **kw): self.values['rt']=kw
    def left_joystick(self, **kw): self.values['left']=kw
    def right_joystick(self, **kw): self.values['right']=kw
    def update(self): self.updates+=1

class MergeTests(unittest.TestCase):
    def run_loop(self, physical, auto):
        tree=ast.parse(SOURCE.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AutoY')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='output_loop')
        names={n.attr for n in ast.walk(method) if isinstance(n,ast.Attribute) and n.attr.startswith('XUSB_GAMEPAD_')}
        vg=SimpleNamespace(XUSB_BUTTON=SimpleNamespace(**{n:n for n in names}))
        gp=SimpleNamespace(wButtons=physical,bLeftTrigger=42,bRightTrigger=198,sThumbLX=-12345,sThumbLY=23456,sThumbRX=100,sThumbRY=-200)
        obj=SimpleNamespace(running=True,pad_index=1,pad=Pad(),xinput=SimpleNamespace(get_state=lambda idx:SimpleNamespace(Gamepad=gp)),
                            state_lock=threading.Lock(),auto_y_until=20 if auto else 0,ui_queue=queue.Queue())
        timer=SimpleNamespace(monotonic=lambda:10, sleep=lambda _:setattr(obj,'running',False))
        ns={'vg':vg,'time':timer}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'output_loop','exec'),ns)
        ns['output_loop'](obj)
        self.assertEqual(obj.pad.updates,1)
        return obj.pad
    def test_physical_a_and_auto_y_merge(self):
        pad=self.run_loop(0x1000,True)
        self.assertEqual(pad.buttons,{'XUSB_GAMEPAD_A','XUSB_GAMEPAD_Y'})
        self.assertEqual(pad.values['left'],{'x_value':-12345,'y_value':23456})
        self.assertEqual(pad.values['right'],{'x_value':100,'y_value':-200})
        self.assertEqual(pad.values['lt'],{'value':42})
        self.assertEqual(pad.values['rt'],{'value':198})
    def test_physical_y_survives_auto_release(self):
        self.assertEqual(self.run_loop(0x8000,False).buttons,{'XUSB_GAMEPAD_Y'})
    def test_no_y_when_neither_source_pressed(self):
        self.assertEqual(self.run_loop(0,False).buttons,set())
    def test_physical_b_x_and_dpad_preserved(self):
        self.assertEqual(self.run_loop(0x6004,False).buttons,{'XUSB_GAMEPAD_B','XUSB_GAMEPAD_X','XUSB_GAMEPAD_DPAD_LEFT'})

if __name__ == '__main__': unittest.main()
