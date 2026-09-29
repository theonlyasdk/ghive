"""Thread-safe asynchronous task runner for Tkinter."""

import queue
import sys
import threading
from typing import Any, Callable, Optional


class AsyncRunner:
    """Dispatches background tasks on worker threads and dispatches callbacks onto Tkinter's main loop."""

    def __init__(self, root: Any):
        """Initialize the async runner with a Tkinter root widget."""
        self.root = root
        self._queue: queue.Queue = queue.Queue()
        self._polling = False
        self._start_polling()

    def _start_polling(self) -> None:
        if not self._polling:
            self._polling = True
            self._poll_queue()

    def _poll_queue(self) -> None:
        try:
            while True:
                callback, args = self._queue.get_nowait()
                try:
                    if callback:
                        callback(*args)
                except Exception as e:
                    print(f"[AsyncRunner] Callback execution error: {e}", file=sys.stderr)
        except queue.Empty:
            pass
        finally:
            try:
                if self.root and self.root.winfo_exists():
                    self.root.after(40, self._poll_queue)
            except Exception:
                pass

    def run(
        self,
        task_func: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[dict] = None,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> threading.Thread:
        """Run a task in a background daemon thread.

        Args:
            task_func: Callable to execute in background thread.
            args: Positional arguments for task_func.
            kwargs: Keyword arguments for task_func.
            on_success: Callback with result, invoked on main thread.
            on_error: Callback with Exception, invoked on main thread.
            on_complete: Callback invoked on main thread after success/error.
        """
        if kwargs is None:
            kwargs = {}

        def _worker():
            try:
                result = task_func(*args, **kwargs)
                if on_success:
                    self._queue.put((on_success, (result,)))
            except Exception as exc:
                if on_error:
                    self._queue.put((on_error, (exc,)))
                else:
                    print(f"[AsyncRunner] Unhandled worker exception: {exc}", file=sys.stderr)
            finally:
                if on_complete:
                    self._queue.put((on_complete, ()))

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return thread
