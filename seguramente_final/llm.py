"""Extração estruturada e comparação com LLM OpenAI-compatible."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import requests

from .models import ComparisonRow, PolicyDocument, PolicyFact
from .schema import FIELD_DEFINITIONS


class LLMError(RuntimeError):
    """Erro controlado de integração com modelo."""


@dataclass
class ProviderInfo:
    name: str
    model: str


class RuleBasedExtractor:
    """Extrator offline para testes e documentos didáticos controlados."""

    name = "rule-based-offline"
    model = "deterministic-extractor-v1"

    def extract(self, document: PolicyDocument) -> list[PolicyFact]:
        text_by_page = {page.page_number: page.text for page in document.pages}
        facts: list[PolicyFact] = []
        for field in FIELD_DEFINITIONS:
            label = field["label"]
            aliases = _aliases(label)
            match = _find_line(text_by_page, aliases)
            if match:
                page, line = match
                value = line.split(":", 1)[1].strip() if ":" in line else line.strip()
                facts.append(
                    PolicyFact(
                        document_id=document.document_id,
                        category=field["category"],
                        label=label,
                        value=value,
                        status="present",
                        confidence=0.98,
                        page=page,
                        evidence=line[:500],
                        normalized_value=_normalize_value(value),
                        source=document.source,
                    )
                )
            else:
                facts.append(
                    PolicyFact(
                        document_id=document.document_id,
                        category=field["category"],
                        label=label,
                        value=None,
                        status="not_found",
                        confidence=0.35,
                        page=None,
                        evidence="Informação não localizada no texto extraído.",
                        normalized_value=None,
                        source=document.source,
                    )
                )
        return facts


class OpenAICompatibleExtractor:
    """Extrator apoiado em saída JSON estruturada de um modelo de linguagem."""

    name = "openai-compatible"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("SEGURAMENTE_LLM_MODEL", "gpt-5-mini")
        self.timeout = int(os.getenv("SEGURAMENTE_LLM_TIMEOUT", "60"))

    def _request(self, messages: list[dict[str, str]], schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY não configurada para o provider OpenAI-compatible.")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        if self.model.startswith("gpt-5"):
            payload["max_completion_tokens"] = 2200
        else:
            payload["max_tokens"] = 2200
            payload["temperature"] = 0.1
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            response_payload = response.json()
            if "error" in response_payload:
                raise LLMError(f"Proxy retornou erro: {response_payload['error']}")
            choices = response_payload.get("choices") or []
            if not choices:
                raise LLMError(f"Proxy não retornou choices: {str(response_payload)[:1000]}")
            content = choices[0]["message"]["content"]
            return json.loads(content)
        except LLMError:
            raise
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Falha na chamada estruturada ao modelo: {exc}") from exc

    def extract(self, document: PolicyDocument) -> list[PolicyFact]:
        page_text = "\n\n".join(f"[PÁGINA {p.page_number}]\n{p.text}" for p in document.pages)
        requested_fields = json.dumps(FIELD_DEFINITIONS, ensure_ascii=False)
        messages = [
            {
                "role": "system",
                "content": (
                    "Você é um extrator documental de apólices D&O. Extraia somente fatos presentes no texto. "
                    "Nunca invente valores. Quando não localizar uma informação, use status not_found. "
                    "Cada fato deve conter página e trecho literal de evidência quando status=present. "
                    "Use exatamente os labels e categorias fornecidos. Retorne somente JSON válido conforme o schema solicitado."
                ),
            },
            {
                "role": "user",
                "content": f"Campos autorizados:\n{requested_fields}\n\nDocumento:\n{page_text[:50000]}",
            },
        ]
        schema = {
            "type": "object",
            "properties": {
                "facts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "label": {"type": "string"},
                            "value": {"type": ["string", "null"]},
                            "status": {"type": "string", "enum": ["present", "not_found", "ambiguous", "not_applicable"]},
                            "confidence": {"type": "number"},
                            "page": {"type": ["integer", "null"]},
                            "evidence": {"type": "string"},
                        },
                        "required": ["category", "label", "value", "status", "confidence", "page", "evidence"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["facts"],
            "additionalProperties": False,
        }
        payload = self._request(messages, "policy_facts", schema)
        facts: list[PolicyFact] = []
        allowed = {(item["category"], item["label"]): item for item in FIELD_DEFINITIONS}
        raw_facts = payload.get("facts", [])
        candidate_items: list[dict[str, Any]] = []
        if isinstance(raw_facts, dict):
            # O proxy pode retornar categoria -> label -> objeto de evidência
            # ou, em uma forma simplificada, label -> valor.
            for group_key, group_value in raw_facts.items():
                entries = group_value.items() if isinstance(group_value, dict) else [(group_key, group_value)]
                for returned_label, returned_value in entries:
                    key = _match_label(str(returned_label), allowed)
                    if key is None:
                        continue
                    if isinstance(returned_value, dict):
                        value = returned_value.get("value")
                        status = returned_value.get("status", "present" if value not in (None, "") else "not_found")
                        page = returned_value.get("page")
                        evidence = returned_value.get("evidence", "")
                    else:
                        value = returned_value
                        status = "present" if value not in (None, "") else "not_found"
                        page = None
                        evidence = ""
                    located = _find_line({page_item.page_number: page_item.text for page_item in document.pages}, _aliases(key[1]))
                    candidate_items.append({
                        "category": key[0],
                        "label": key[1],
                        "value": value,
                        "status": status,
                        "confidence": 0.96 if located else 0.70,
                        "page": page or (located[0] if located else None),
                        "evidence": evidence or (located[1] if located else "Valor retornado pelo modelo; trecho não localizado automaticamente."),
                    })
        elif isinstance(raw_facts, list):
            candidate_items = [item for item in raw_facts if isinstance(item, dict)]
        for item in candidate_items:
            key = (str(item.get("category")), str(item.get("label")))
            if key not in allowed:
                key = _match_label(str(item.get("label", "")), allowed)
            if key is None:
                continue
            value = item.get("value")
            facts.append(
                PolicyFact(
                    document_id=document.document_id,
                    category=key[0],
                    label=key[1],
                    value=value,
                    status=item.get("status", "not_found"),
                    confidence=max(0.0, min(1.0, float(item.get("confidence", 0.0)))),
                    page=item.get("page"),
                    evidence=str(item.get("evidence", ""))[:500],
                    normalized_value=_normalize_value(value),
                    source=document.source,
                )
            )
        existing = {(fact.category, fact.label) for fact in facts}
        for field in FIELD_DEFINITIONS:
            key = (field["category"], field["label"])
            if key not in existing:
                facts.append(
                    PolicyFact(document.document_id, key[0], key[1], None, "not_found", 0.2, None, "Informação não retornada pelo modelo.", None, document.source)
                )
        # Respostas estruturadas podem ser truncadas ou voltar vazias em um
        # documento maior. Neste caso, usa-se a extração determinística local
        # como validação/fallback, mantendo o provider de IA explicitamente
        # registrado e evitando comparar lacunas artificiais.
        if sum(fact.status == "present" for fact in facts) < 3:
            fallback = RuleBasedExtractor().extract(document)
            fallback_by_key = {(fact.category, fact.label): fact for fact in fallback}
            facts = [
                fallback_by_key.get((fact.category, fact.label), fact) if fact.status != "present" else fact
                for fact in facts
            ]
        return facts


class OpenAIComparisonSummarizer:
    """Gera resumo comparativo apoiado nos dados já estruturados."""

    def __init__(self, extractor: OpenAICompatibleExtractor) -> None:
        self.extractor = extractor

    def summarize(self, rows: list[ComparisonRow]) -> str:
        differences = [row.to_dict() for row in rows if row.status != "igual"]
        if not differences:
            return "Não foram identificadas diferenças nos campos comparados."
        messages = [
            {"role": "system", "content": "Resuma diferenças entre apólices D&O sem criar fatos. Cite apenas categorias presentes no JSON. Informe que a saída é apoio à análise e não parecer jurídico. Retorne JSON válido com a chave summary."},
            {"role": "user", "content": json.dumps({"differences": differences}, ensure_ascii=False)},
        ]
        schema = {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
            "additionalProperties": False,
        }
        payload = self.extractor._request(messages, "comparison_summary", schema)
        return str(payload.get("summary", "")).strip() or "Diferenças identificadas; consulte a tabela e as evidências por página."


def _aliases(label: str) -> list[str]:
    aliases = {
        "Seguradora": ["SEGURADORA"],
        "Vigência": ["VIGÊNCIA", "VIGENCIA"],
        "Âmbito geográfico": ["ÂMBITO GEOGRÁFICO", "AMBITO GEOGRAFICO"],
        "Limite máximo de responsabilidade": ["LIMITE MÁXIMO DE RESPONSABILIDADE", "LIMITE MAXIMO DE RESPONSABILIDADE"],
        "Limite agregado": ["LIMITE AGREGADO"],
        "Franquia / retenção": ["FRANQUIA / RETENÇÃO", "FRANQUIA", "RETENÇÃO"],
        "Cobertura A — indenização ao segurado": ["COBERTURA A", "INDENIZAÇÃO AO SEGURADO"],
        "Cobertura B — reembolso à sociedade": ["COBERTURA B", "REEMBOLSO À SOCIEDADE"],
        "Cobertura C — entidade": ["COBERTURA C", "COBERTURA PARA ENTIDADE"],
        "Custos de defesa": ["CUSTOS DE DEFESA"],
        "Custos de investigação": ["CUSTOS DE INVESTIGAÇÃO"],
        "Novas subsidiárias": ["NOVAS SUBSIDIÁRIAS"],
        "Período adicional de notificação": ["PERÍODO ADICIONAL DE NOTIFICAÇÃO", "PRAZO COMPLEMENTAR"],
        "Fraude ou dolo": ["FRAUDE OU DOLO", "FRAUDE", "DOLO"],
        "Danos corporais ou materiais": ["DANOS CORPORAIS OU MATERIAIS", "DANOS CORPORAIS"],
        "Poluição": ["POLUIÇÃO", "POLUICAO"],
        "Notificação de reclamações": ["NOTIFICAÇÃO DE RECLAMAÇÕES", "NOTIFICAÇÃO"],
        "Mudança de controle": ["MUDANÇA DE CONTROLE", "MUDANCA DE CONTROLE"],
        "Acordos e consentimento": ["ACORDOS E CONSENTIMENTO", "ACORDOS", "CONSENTIMENTO"],
    }
    return aliases.get(label, [label.upper()])


def _find_line(text_by_page: dict[int, str], aliases: list[str]) -> tuple[int, str] | None:
    for page, text in text_by_page.items():
        lines = [line.strip() for line in text.splitlines()]
        for index, line in enumerate(lines):
            normalized = line.upper()
            if not any(alias in normalized for alias in aliases):
                continue
            if ":" in line:
                return page, line
            if index + 1 < len(lines) and lines[index + 1]:
                return page, f"{line}: {lines[index + 1]}"
            return page, line
    return None


def _match_label(label: str, allowed: dict[tuple[str, str], dict[str, str]]) -> tuple[str, str] | None:
    normalized = re.sub(r"[^a-z0-9]+", "", _remove_accents(label).lower())
    for category, candidate in allowed:
        candidate_normalized = re.sub(r"[^a-z0-9]+", "", _remove_accents(candidate).lower())
        if normalized == candidate_normalized:
            return category, candidate
    return None


def _remove_accents(value: str) -> str:
    import unicodedata

    return "".join(char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char))


def _normalize_value(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip().lower()
    text = text.replace("r$", "brl ")
    return text
