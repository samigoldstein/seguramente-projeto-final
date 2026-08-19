"""Interface do MVP D&O Policy Intelligence."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from seguramente_final.pipeline import analyze_policies

load_dotenv()
ROOT = Path(__file__).resolve().parent
DEFAULT_A = ROOT / "data" / "policies" / "Apolice_DO_A.pdf"
DEFAULT_B = ROOT / "data" / "policies" / "Apolice_DO_B.pdf"
DB_PATH = ROOT / "data" / "policies.db"

st.set_page_config(page_title="D&O Policy Intelligence", page_icon="", layout="wide")
st.title("D&O Policy Intelligence")
st.caption("Projeto Final InsurMinds — análise e comparação explicável de apólices D&O")

with st.sidebar:
    st.header("Documentos")
    use_demo = st.checkbox("Usar corpus sintético incluso", value=True)
    if use_demo:
        file_a = DEFAULT_A
        file_b = DEFAULT_B
        st.info("Corpus autoral sintético, criado exclusivamente para demonstração acadêmica.")
    else:
        upload_a = st.file_uploader("Apólice A — PDF ou imagem", type=["pdf", "png", "jpg", "jpeg", "tif", "tiff"], key="a")
        upload_b = st.file_uploader("Apólice B — PDF ou imagem", type=["pdf", "png", "jpg", "jpeg", "tif", "tiff"], key="b")
        file_a = file_b = None
    provider = st.selectbox("Modo de IA", ["offline", "openai"], help="Offline usa regras determinísticas para demonstração. OpenAI usa extração JSON estruturada por modelo de linguagem.")
    run = st.button("Analisar e comparar", type="primary", use_container_width=True)
    st.divider()
    st.caption("A saída é apoio à análise. Não constitui parecer jurídico, subscrição ou decisão de cobertura.")

if not use_demo and run:
    if not upload_a or not upload_b:
        st.error("Faça upload de duas apólices para comparar.")
        st.stop()
    temp_dir = Path(tempfile.mkdtemp(prefix="seguramente-do-"))
    file_a = temp_dir / upload_a.name
    file_b = temp_dir / upload_b.name
    file_a.write_bytes(upload_a.getbuffer())
    file_b.write_bytes(upload_b.getbuffer())

if run:
    try:
        with st.spinner("Extraindo, estruturando e comparando os documentos..."):
            result = analyze_policies([file_a, file_b], names=["Apólice A", "Apólice B"], provider_mode=provider, store_path=DB_PATH)
        st.session_state.result = result
        st.success("Análise concluída. Revise as evidências antes de usar o resultado.")
    except Exception as exc:
        st.error(str(exc))

result = st.session_state.get("result")
if result is None:
    st.markdown("""### Fluxo demonstrável\n\n1. Receba duas apólices em PDF ou imagem.\n2. Extraia o texto por página, usando PDF nativo ou OCR.\n3. Estruture campos D&O com evidências.\n4. Consulte e compare as apólices.\n5. Revise as diferenças na tabela comparativa.""")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Documentos", len(result.documents))
col2.metric("Campos comparados", len(result.comparison))
col3.metric("Diferenças/lacunas", sum(row.status not in {"igual", "ambos_ausentes"} for row in result.comparison))
col4.metric("Provider", result.provider)

st.header("1. Documentos recebidos e extração")
doc_cols = st.columns(len(result.documents))
for col, document in zip(doc_cols, result.documents):
    with col:
        st.subheader(document.name)
        st.write(f"**ID:** `{document.document_id}`")
        st.write(f"**Páginas:** {len(document.pages)}")
        st.write(f"**Origem:** {document.source}")
        methods = pd.Series([page.extraction_method for page in document.pages]).value_counts().to_dict()
        st.write(f"**Métodos:** {methods}")

st.header("2. Resumo comparativo")
st.info(result.executive_summary)

st.header("3. Consulta estruturada")
query = st.text_input("Pesquisar categoria, campo ou valor", placeholder="Ex.: limite, cobertura, franquia, poluição")
rows = result.comparison
if query.strip():
    needle = query.lower()
    rows = [row for row in rows if needle in " ".join(str(value or "") for value in [row.category, row.label, row.policy_a, row.policy_b, row.difference, row.evidence_a, row.evidence_b]).lower()]
comparison_df = pd.DataFrame([
    {
        "Categoria": row.category,
        "Campo": row.label,
        "Apólice A": row.policy_a or "Não localizado",
        "Apólice B": row.policy_b or "Não localizado",
        "Status": row.status,
        "Diferença": row.difference,
        "Páginas": f"A:{row.page_a or '-'} | B:{row.page_b or '-'}",
    }
    for row in rows
])
st.dataframe(comparison_df, use_container_width=True, hide_index=True)

st.header("4. Evidências por página")
for row in rows:
    if row.status == "igual" and not query.strip():
        continue
    with st.expander(f"{row.label} — {row.status}"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Apólice A — página {row.page_a or 'não localizada'}**")
            st.write(row.evidence_a)
        with c2:
            st.markdown(f"**Apólice B — página {row.page_b or 'não localizada'}**")
            st.write(row.evidence_b)

st.header("5. Limitações")
st.warning("Os documentos sintéticos e as regras de comparação são didáticos. A aplicação não substitui revisão jurídica, subscrição ou análise integral das condições particulares.")
