"""Modelos de datos de EON."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserRequest:
    text: str
    files: list[str] = field(default_factory=list)


@dataclass
class ClarifyingQuestion:
    field: str
    question: str


@dataclass
class ParsedIntent:
    action: str
    client_name: str | None = None
    quote_id: str | None = None
    project_type: str | None = None
    tags: list[str] = field(default_factory=list)
    needs_files: bool = False
    confidence: float = 1.0
    missing_fields: list[str] = field(default_factory=list)


@dataclass
class EONResult:
    success: bool
    action: str
    data: Any = None
    summary: str = ""
    questions: list[ClarifyingQuestion] = field(default_factory=list)
    error: str = ""
    details: dict = field(default_factory=dict)
