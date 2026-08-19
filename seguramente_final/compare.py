"""Comparação explicável de fatos extraídos de duas apólices."""

from __future__ import annotations

from .models import ComparisonRow, PolicyDocument, PolicyFact
from .schema import FIELD_DEFINITIONS


def compare_documents(document_a: PolicyDocument, document_b: PolicyDocument) -> list[ComparisonRow]:
    facts_a = {(fact.category, fact.label): fact for fact in document_a.facts}
    facts_b = {(fact.category, fact.label): fact for fact in document_b.facts}
    rows: list[ComparisonRow] = []
    for field in FIELD_DEFINITIONS:
        key = (field["category"], field["label"])
        fact_a = facts_a.get(key) or _not_found(document_a.document_id, key)
        fact_b = facts_b.get(key) or _not_found(document_b.document_id, key)
        status, difference = _compare_values(fact_a, fact_b)
        rows.append(
            ComparisonRow(
                category=key[0],
                label=key[1],
                policy_a=fact_a.value,
                policy_b=fact_b.value,
                difference=difference,
                status=status,
                evidence_a=fact_a.evidence,
                evidence_b=fact_b.evidence,
                page_a=fact_a.page,
                page_b=fact_b.page,
            )
        )
    return rows


def _compare_values(a: PolicyFact, b: PolicyFact) -> tuple[str, str]:
    if a.status == "not_found" and b.status == "not_found":
        return "ambos_ausentes", "Campo não localizado nos dois documentos"
    if a.status == "not_found":
        return "ausente_em_a", "Campo localizado somente na apólice B"
    if b.status == "not_found":
        return "ausente_em_b", "Campo localizado somente na apólice A"
    if a.status == "ambiguous" or b.status == "ambiguous":
        return "ambigua", "Requer revisão humana por ambiguidade na extração"
    if a.normalized_value == b.normalized_value:
        return "igual", "Valores equivalentes no texto normalizado"
    return "diferente", "Valores ou condições diferentes"


def _not_found(document_id: str, key: tuple[str, str]) -> PolicyFact:
    return PolicyFact(document_id, key[0], key[1], None, "not_found", 0.0, None, "Informação não localizada.")
