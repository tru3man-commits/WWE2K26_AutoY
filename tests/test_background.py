import threading
import time
import unittest
from background import BackgroundJob


class BackgroundTests(unittest.TestCase):
    def result(self, job):
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            result=job.poll()
            if result is not None: return result
            time.sleep(.005)
        self.fail('Background result did not arrive')

    def test_slow_work_does_not_block_caller(self):
        gate=threading.Event(); job=BackgroundJob()
        try:
            job.start(lambda: gate.wait(2))
            self.assertIsNone(job.poll())
            gate.set()
            self.assertEqual(self.result(job),(True,True))
        finally: gate.set()

    def test_worker_is_not_gui_thread(self):
        main=threading.get_ident(); job=BackgroundJob()
        job.start(threading.get_ident)
        ok,identity=self.result(job)
        self.assertTrue(ok); self.assertNotEqual(main,identity)
