from pathlib import Path

import pytest

from seguramente_final.compare import compare_documents
from seguramente_final.ingest import IngestionError, load_document
from seguramente_final.pipeline import analyze_policies
from seguramente_final.storage import PolicyStore

ROOT = Path(__file__).resolve().parents[1]
POLICY_A = ROOT / "data" / "policies" / "Apolice_DO_A.pdf"
POLICY_B = ROOT / "data" / "policies" / "Apolice_DO_B.pdf"


def test_ingestao_pdf_preserva_paginas_e_texto():
    document = load_document(POLICY_A, name="A")
    assert document.document_id
    assert len(document.pages) == 3
    assert any("LIMITE MÁXIMO DE RESPONSABILIDADE" in page.text for page in document.pages)
    assert all(page.extraction_method.startswith("pdf") or page.extraction_method == "ocr" for page in document.pages)


def test_pipeline_offline_extrai_e_compara_duas_apolices(tmp_path):
    result = analyze_policies([POLICY_A, POLICY_B], provider_mode="offline", store_path=tmp_path / "policies.db")
    assert len(result.documents) == 2
    assert len(result.comparison) >= 10
    limits = [row for row in result.comparison if row.label == "Limite máximo de responsabilidade"]
    assert limits[0].status == "diferente"
    assert "10.000.000" in (limits[0].policy_a or "")
    assert "15.000.000" in (limits[0].policy_b or "")
    assert limits[0].page_a is not None
    assert limits[0].page_b is not None


def test_storage_registra_documentos_paginas_fatos_e_comparacoes(tmp_path):
    db = tmp_path / "policies.db"
    result = analyze_policies([POLICY_A, POLICY_B], provider_mode="offline", store_path=db)
    counts = PolicyStore(db).counts()
    assert counts["documents"] == 2
    assert counts["pages"] == 6
    assert counts["facts"] >= 30
    assert counts["comparisons"] == len(result.comparison)


def test_comparacao_explicita_diferenca_evidencia():
    result = analyze_policies([POLICY_A, POLICY_B], provider_mode="offline", store_path=ROOT / "data" / "test_policies.db")
    row = next(item for item in result.comparison if item.label == "Período adicional de notificação")
    assert row.status == "diferente"
    assert row.evidence_a
    assert row.evidence_b


def test_pipeline_exige_duas_apolices(tmp_path):
    with pytest.raises(ValueError):
        analyze_policies([POLICY_A], provider_mode="offline", store_path=tmp_path / "policies.db")


def test_formato_invalido_e_rejeitado(tmp_path):
    invalid = tmp_path / "documento.txt"
    invalid.write_text("texto")
    with pytest.raises(IngestionError):
        load_document(invalid)
