"""Isolated PyMuPDF jobs. Never invoke PyMuPDF from a worker thread."""
import multiprocessing as mp
import queue

import pymupdf
from PySide6.QtCore import QObject, QTimer, Signal


def _run_job(output, operation, arguments):
    try:
        if operation == "search":
            path, query = arguments
            with pymupdf.open(path) as document:
                for number, page in enumerate(document):
                    rects = [tuple(rect) for rect in page.search_for(query)]
                    if rects:
                        output.put(("hits", (number, rects)))
                    if number % 100 == 0:
                        output.put(("progress", (number + 1, document.page_count)))
        elif operation == "index":
            from .db import complete_body_index
            complete_body_index(*arguments, progress=lambda done, total:
                                output.put(("progress", (done, total))))
        elif operation == "mail_body":
            from .db import complete_body_index, get_body_text
            path, index_path, mail_id = arguments
            complete_body_index(path, index_path, "mail", only_row_id=mail_id)
            output.put(("body", get_body_text(index_path, mail_id)))
        elif operation == "notes_load":
            from .sticky_notes import load_notes
            result = load_notes(*arguments, progress=lambda done, total:
                                output.put(("progress", (done, total))))
            output.put(("notes", result))
        elif operation == "notes_prepare":
            from .sticky_notes import prepare_save
            result = prepare_save(*arguments, progress=lambda done, total:
                                  output.put(("progress", (done, total))))
            output.put(("prepared", result))
        elif operation == "notes_commit":
            from .sticky_notes import commit_save
            output.put(("committed", commit_save(*arguments)))
        output.put(("done", None))
    except Exception as error:
        output.put(("error", str(error)))


def _render_tiles(requests, output, path):
    try:
        with pymupdf.open(path) as document:
            stripped = set()
            while True:
                key, clip = requests.get()
                number, scale, _x, _y, dpr = key
                try:
                    page = document[number]
                    # Text notes are a GUI overlay. Preserve every other annotation.
                    if number not in stripped:
                        for annot in list(page.annots(types=[pymupdf.PDF_ANNOT_TEXT]) or ()):
                            page.delete_annot(annot)
                        stripped.add(number)
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale * dpr, scale * dpr),
                        clip=pymupdf.Rect(clip), colorspace=pymupdf.csRGB, alpha=False)
                    output.put((key, (pix.width, pix.height, pix.stride, pix.samples)))
                except Exception as error:
                    output.put((key, str(error)))
    except Exception as error:
        output.put((None, str(error)))


class TileRenderer(QObject):
    ready = Signal(object, object)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self._process = None
        self._requests = None
        self._output = None
        self._pending = set()
        self._exit_seen = False
        self._timer = QTimer(self)
        self._timer.setInterval(20)
        self._timer.timeout.connect(self._poll)

    def request(self, key, clip):
        if key in self._pending:
            return
        if self._process is None:
            context = mp.get_context("spawn")
            self._requests = context.Queue(maxsize=32)
            self._output = context.Queue(maxsize=8)
            self._process = context.Process(target=_render_tiles,
                args=(self._requests, self._output, self.path), daemon=True)
            try:
                self._process.start()
                self._timer.start()
            except Exception:
                self.stop()
                raise
        try:
            self._requests.put_nowait((key, tuple(clip)))
            self._pending.add(key)
        except queue.Full:
            pass

    def _poll(self):
        for _ in range(8):
            try:
                key, payload = self._output.get_nowait()
            except queue.Empty:
                if self._process is not None and not self._process.is_alive():
                    if self._exit_seen:
                        self.stop()
                        self.ready.emit(None, "PDF描画プロセスが終了しました")
                    else:
                        self._exit_seen = True
                return
            self._pending.discard(key)
            if key is None:
                self.stop()
                self.ready.emit(key, payload)
                return
            self.ready.emit(key, payload)

    def stop(self):
        self._timer.stop()
        if self._process is not None:
            if self._process.pid is not None:
                if self._process.is_alive():
                    self._process.terminate()
                self._process.join(timeout=1)
            self._process.close()
            self._process = None
        for messages in (self._requests, self._output):
            if messages is not None:
                messages.cancel_join_thread()
                messages.close()
        self._requests = self._output = None
        self._pending.clear()
        self._exit_seen = False


class PdfJob(QObject):
    message = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = None
        self._queue = None
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._poll)
        self.destroyed.connect(self.stop)

    def start(self, operation, *arguments):
        self.stop()
        context = mp.get_context("spawn")
        self._queue = context.Queue(maxsize=64)
        self._process = context.Process(target=_run_job,
                                        args=(self._queue, operation, arguments), daemon=True)
        try:
            self._process.start()
            self._timer.start()
        except Exception:
            self.stop()
            raise

    def _poll(self):
        messages = self._queue
        if messages is None:
            return
        for _ in range(64):
            try:
                kind, value = messages.get_nowait()
            except queue.Empty:
                if self._process is not None and not self._process.is_alive():
                    # Queue feeder may deliver after process exit; next timer tick drains it.
                    if getattr(self, "_exit_seen", False):
                        self.stop()
                        self.message.emit("error", "PDF処理プロセスが終了しました")
                    else:
                        self._exit_seen = True
                return
            if kind in ("done", "error"):
                self.stop()
                self.message.emit(kind, value)
                return
            self.message.emit(kind, value)
            if self._queue is not messages:
                return

    def stop(self, *_args):
        self._timer.stop()
        process, self._process = self._process, None
        if process is not None:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=1)
            process.close()
        messages, self._queue = self._queue, None
        if messages is not None:
            messages.cancel_join_thread()
            messages.close()
        self._exit_seen = False
