"""Orquestração do MVP D&O."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .compare import compare_documents
from .ingest import load_document
from .llm import OpenAICompatibleExtractor, OpenAIComparisonSummarizer, RuleBasedExtractor
from .models import AnalysisResult, PolicyDocument
from .storage import PolicyStore


def analyze_policies(
    paths: Iterable[str | Path],
    names: Iterable[str] | None = None,
    source: str = "documento fornecido para demonstração",
    provider_mode: str = "offline",
    store_path: str | Path = "data/policies.db",
) -> AnalysisResult:
    """Executa as sete etapas preferenciais do edital."""

    path_list = list(paths)
    if len(path_list) < 2:
        raise ValueError("A comparação exige pelo menos duas apólices.")
    name_list = list(names or [])
    documents = [
        load_document(
            path,
            name=name_list[index] if index < len(name_list) else Path(path).name,
            source=source,
        )
        for index, path in enumerate(path_list)
    ]
    if provider_mode in {"openai", "openai-compatible"}:
        extractor = OpenAICompatibleExtractor()
        provider_name, model = extractor.name, extractor.model
    elif provider_mode == "offline":
        extractor = RuleBasedExtractor()
        provider_name, model = extractor.name, extractor.model
    else:
        raise ValueError("provider_mode deve ser 'offline' ou 'openai'.")
    for document in documents:
        document.facts = extractor.extract(document)
    rows = compare_documents(documents[0], documents[1])
    if provider_mode in {"openai", "openai-compatible"}:
        summary = OpenAIComparisonSummarizer(extractor).summarize(rows)
    else:
        summary = _offline_summary(rows)
    store = PolicyStore(store_path)
    for document in documents:
        store.save_document(document)
    store.save_comparison(documents[0], documents[1], rows)
    return AnalysisResult(documents, rows, summary, provider_name, model)


def _offline_summary(rows: list) -> str:
    differences = [row for row in rows if row.status not in {"igual", "ambos_ausentes"}]
    if not differences:
        return "Não foram identificadas diferenças nos campos comparados."
    categories: dict[str, int] = {}
    for row in differences:
        categories[row.category] = categories.get(row.category, 0) + 1
    category_text = ", ".join(f"{key} ({value})" for key, value in categories.items())
    return (
        f"Foram identificadas {len(differences)} diferenças ou lacunas nas categorias {category_text}. "
        "A comparação é um apoio à análise e deve ser revisada contra o texto original das apólices; não constitui parecer jurídico."
    )
