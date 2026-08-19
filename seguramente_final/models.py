"""Modelos de domínio do Projeto Final D&O."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

FactStatus = Literal["present", "not_found", "ambiguous", "not_applicable"]


@dataclass
class DocumentPage:
    document_id: str
    page_number: int
    text: str
    extraction_method: str


@dataclass
class PolicyFact:
    document_id: str
    category: str
    label: str
    value: str | None
    status: FactStatus
    confidence: float
    page: int | None
    evidence: str
    normalized_value: str | None = None
    source: str | None = None


@dataclass
class PolicyDocument:
    document_id: str
    name: str
    path: str
    source: str
    pages: list[DocumentPage] = field(default_factory=list)
    facts: list[PolicyFact] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonRow:
    category: str
    label: str
    policy_a: str | None
    policy_b: str | None
    difference: str
    status: str
    evidence_a: str
    evidence_b: str
    page_a: int | None
    page_b: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    documents: list[PolicyDocument]
    comparison: list[ComparisonRow]
    executive_summary: str
    provider: str
    model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "documents": [document.to_dict() for document in self.documents],
            "comparison": [row.to_dict() for row in self.comparison],
            "executive_summary": self.executive_summary,
            "provider": self.provider,
            "model": self.model,
        }
