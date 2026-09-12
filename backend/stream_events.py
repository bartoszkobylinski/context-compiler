from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Callable


_EventSink = Callable[[Any], None]
_event_sink: ContextVar[_EventSink | None] = ContextVar("context_compiler_event_sink", default=None)


class EventList(list):
    """List that mirrors appended agent events to an optional per-run sink.

    Normal compiler runs behave exactly like a regular list. Streaming runs set a
    context-local sink in the worker thread so each event can be forwarded to the UI
    as soon as it is produced.
    """

    def append(self, item: Any) -> None:
        super().append(item)
        sink = _event_sink.get()
        if sink is not None:
            sink(item)


def set_event_sink(sink: _EventSink) -> Token:
    return _event_sink.set(sink)


def reset_event_sink(token: Token) -> None:
    _event_sink.reset(token)
