"""Synchronous worker-to-Qt dialog requests.

A PDF worker may need an answer before it can continue. The callable runs only
on the QApplication thread; the worker blocks on a threading.Event.
"""
from dataclasses import dataclass, field
from threading import Event, Lock

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication


@dataclass(eq=False)
class DialogRequest:
    callback: object
    default: object
    completed: Event = field(default_factory=Event)
    result: object = None
    error: BaseException | None = None


class QtDialogBridge(QObject):
    requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication must exist before QtDialogBridge")
        self._pending = set()
        self._lock = Lock()
        self._closed = False
        self.requested.connect(self._execute)
        app.aboutToQuit.connect(self.close)

    def invoke(self, callback, default=None):
        if QThread.currentThread() == self.thread():
            return callback()
        request = DialogRequest(callback, default)
        with self._lock:
            if self._closed:
                return default
            self._pending.add(request)
        self.requested.emit(request)
        request.completed.wait()
        if request.error is not None:
            raise request.error
        return request.result

    @Slot(object)
    def _execute(self, request):
        with self._lock:
            if self._closed or request not in self._pending:
                return
        try:
            request.result = request.callback()
        except BaseException as exc:
            request.error = exc
        finally:
            with self._lock:
                self._pending.discard(request)
            request.completed.set()

    @Slot()
    def close(self):
        with self._lock:
            self._closed = True
            pending = tuple(self._pending)
            self._pending.clear()
        for request in pending:
            request.result = request.default
            request.completed.set()