"""QThread + QObject worker that runs SearchManager off the Qt GUI thread.

The GUI must never block on network I/O. This worker owns its own asyncio
event loop on a background thread and emits Qt signals back to the GUI
thread for state changes, partial (progressive) results, and completion.
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QObject, QThread, Signal

from core.models import SearchMode, SearchResponse, SearchResult, SearchState
from core.search_manager import SearchManager


class SearchWorker(QObject):
    state_changed = Signal(str, dict)
    partial_results = Signal(list)
    finished = Signal(object)  # SearchResponse

    def __init__(self, manager: SearchManager, username: str, mode: SearchMode, force_refresh: bool = False):
        super().__init__()
        self._manager = manager
        self._username = username
        self._mode = mode
        self._force_refresh = force_refresh

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                self._manager.search(
                    self._username,
                    mode=self._mode,
                    force_refresh=self._force_refresh,
                    on_state_change=self._emit_state,
                    on_partial_results=self._emit_partial,
                )
            )
        finally:
            loop.close()

        self.finished.emit(response)

    def _emit_state(self, state: SearchState, extra: dict):
        self.state_changed.emit(state.value, extra)

    def _emit_partial(self, results):
        self.partial_results.emit(list(results))

    def cancel(self):
        self._manager.cancel()


def start_search(
    manager: SearchManager,
    username: str,
    mode: SearchMode,
    force_refresh: bool,
    on_state_changed,
    on_partial_results,
    on_finished,
):
    """Spin up a QThread running the worker; returns (thread, worker) so the
    caller can keep references alive and call worker.cancel()."""
    thread = QThread()
    worker = SearchWorker(manager, username, mode, force_refresh)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.state_changed.connect(on_state_changed)
    worker.partial_results.connect(on_partial_results)
    # on_finished is responsible for retiring/joining the thread (see
    # MainWindow._retire_thread) so we don't race thread.quit()/deleteLater()
    # against the OS thread still shutting down.
    worker.finished.connect(on_finished)

    thread.start()
    return thread, worker
