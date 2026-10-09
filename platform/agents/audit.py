"""Audit trail for consequential agent actions (governance)."""

import logging
import time

log = logging.getLogger("retail_ai.audit")


class AuditLog:
    """Records events to the ``retail_ai.audit`` logger and keeps them in memory for inspection.

    Applications can pass a ``sink`` (e.g. a Log Analytics or database writer).
    """

    def __init__(self, sink=None):
        self.events: list[dict] = []
        self._sink = sink

    def record(self, event: str, **details) -> dict:
        entry = {"event": event, "at": time.time(), **details}
        self.events.append(entry)
        log.info(event, extra=details)
        if self._sink:
            self._sink(entry)
        return entry
