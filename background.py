"""Run blocking discovery outside Tk; deliver results only on the GUI thread."""
import queue
import threading
import traceback


class BackgroundJob:
    def __init__(self):
        self.results = queue.Queue()

    def start(self, operation):
        def worker():
            try:
                self.results.put((True, operation()))
            except Exception as exc:
                traceback.print_exc()
                self.results.put((False, exc))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            return self.results.get_nowait()
        except queue.Empty:
            return None
