from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from .stream_events import EventList


@dataclass
class Document:
    id: str
    title: str
    body: str
    published_at: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    supersedes: str | None = None
    authority: str = "unknown"
    domains: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    path: str | None = None


@dataclass
class ToolEvent:
    type: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Evidence:
    claim: str
    source_id: str
    section: str | None = None
    valid_at_query_time: bool | None = None
    authority: str | None = None
    status: Literal["SUPPORTED", "UNSUPPORTED", "CONFLICT", "UNKNOWN"] = "SUPPORTED"


@dataclass
class AgentState:
    question: str
    query_date: date | None
    evidence: list[Evidence] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    visited_documents: set[str] = field(default_factory=set)
    events: list[ToolEvent] = field(default_factory=EventList)
    step: int = 0
    max_steps: int = 22
