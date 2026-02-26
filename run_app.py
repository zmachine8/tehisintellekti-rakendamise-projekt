import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="AI Kursuse Nõustaja (RAG + filtrid)", layout="wide")
st.title("🎓 AI Kursuse Nõustaja (RAG + filtrid)")
st.caption("courses_documents = RAG korpus, courses_metadata = filtrid, OpenRouter = LLM")

BASE = Path(__file__).parent

DOCS_PATH = BASE / "out/courses_documents.csv"
META_PATH = BASE / "out/courses_metadata.csv"

# ---------------------------
# Helpers: safe column pick
# ---------------------------
def first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None

@st.cache_resource
def load_embedder():
    return SentenceTransformer("BAAI/bge-m3")

@st.cache_data
def load_data():
    docs = pd.read_csv(DOCS_PATH)
    meta = pd.read_csv(META_PATH)
    return docs, meta

embedder = load_embedder()
docs_df, meta_df = load_data()

# Expected key columns
docs_key = first_existing_col(docs_df, ["course_uuid", "uuid", "id"])
meta_key = first_existing_col(meta_df, ["course_uuid", "uuid", "id"])

if docs_key is None or meta_key is None:
    st.error("Ei leia join-võtit. Ootan, et mõlemas CSV-s oleks `course_uuid` (või `uuid`/`id`).")
    st.stop()

text_col = first_existing_col(docs_df, ["document_text", "text", "content"])
code_col = first_existing_col(docs_df, ["code", "course_code"])

if text_col is None:
    st.error("Ei leia tekstiveergu. Ootan `document_text` (või `text`/`content`).")
    st.stop()

# Metadata columns (proovime mitut võimalikku nime)
credits_col  = first_existing_col(meta_df, ["credits", "version__credits", "eap"])
semester_col = first_existing_col(meta_df, ["version__target__semester__code", "semester", "semester_code"])
lang_col     = first_existing_col(meta_df, ["version__target__language__code", "language", "lang"])
level_col    = first_existing_col(meta_df, ["study_levels__codes", "version__additional_info__study_levels__codes", "study_level"])

# ---------------------------
# Sidebar: API key + filters
# ---------------------------
with st.sidebar:
    st.subheader("OpenRouter")
    api_key = st.text_input(
        "API key",
        value=os.getenv("OPENROUTER_API_KEY", ""),
        type="password",
        help="OpenRouter key (nt sk-or-v1-...)",
    )

    # Optional but recommended headers for OpenRouter
    site_url = st.text_input("HTTP-Referer (optional)", value="")
    app_title = st.text_input("X-Title (optional)", value="AI Kursuse Nõustaja")

    st.divider()
    st.subheader("Filtrid (metaandmed)")

    # credits filter
    credits_val = None
    if credits_col:
        credits_opts = ["(kõik)"] + sorted([str(x) for x in meta_df[credits_col].dropna().unique().tolist()],
                                           key=lambda s: float(s) if s.replace(".","",1).isdigit() else s)
        credits_val = st.selectbox("EAP / credits", credits_opts, index=0)

    # semester filter
    semester_val = None
    if semester_col:
        sem_opts = ["(kõik)"] + sorted([str(x) for x in meta_df[semester_col].dropna().unique().tolist()])
        semester_val = st.selectbox("Semester", sem_opts, index=0)

    # language filter
    lang_val = None
    if lang_col:
        lang_opts = ["(kõik)"] + sorted([str(x) for x in meta_df[lang_col].dropna().unique().tolist()])
        lang_val = st.selectbox("Keel", lang_opts, index=0)

    # level filter
    level_val = None
    if level_col:
        # study levels võivad olla komadega stringid; jätame lihtsaks: exact match stringile
        lvl_opts = ["(kõik)"] + sorted([str(x) for x in meta_df[level_col].dropna().unique().tolist()])
        level_val = st.selectbox("Õppetase", lvl_opts, index=0)

# ---------------------------
# Chat state
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------------------------
# Main chat input
# ---------------------------
if prompt := st.chat_input("Kirjelda, mida soovid õppida (nt 'masinõpe algajale', 'andmeturve', 'java oop')..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key:
            st.error("Puudub OpenRouter API key. Pane see sidebarisse või env `OPENROUTER_API_KEY`.")
            st.stop()

        # ---- 1) META FILTER ----
        filtered_meta = meta_df.copy()

        if credits_col and credits_val and credits_val != "(kõik)":
            filtered_meta = filtered_meta[filtered_meta[credits_col].astype(str) == str(credits_val)]

        if semester_col and semester_val and semester_val != "(kõik)":
            filtered_meta = filtered_meta[filtered_meta[semester_col].astype(str) == str(semester_val)]

        if lang_col and lang_val and lang_val != "(kõik)":
            filtered_meta = filtered_meta[filtered_meta[lang_col].astype(str) == str(lang_val)]

        if level_col and level_val and level_val != "(kõik)":
            filtered_meta = filtered_meta[filtered_meta[level_col].astype(str) == str(level_val)]

        allowed_ids = set(filtered_meta[meta_key].dropna().astype(str).tolist())

        # ---- 2) JOIN docs + apply allowed_ids ----
        docs_work = docs_df.copy()
        docs_work[docs_key] = docs_work[docs_key].astype(str)

        if allowed_ids:
            docs_work = docs_work[docs_work[docs_key].isin(allowed_ids)]

        if docs_work.empty:
            st.warning("Filtritega ei jäänud ühtegi kursust. Muuda filtreid.")
            st.stop()

        # ---- 3) SEMANTIC SEARCH ----
        with st.spinner("Otsin semantiliselt sobivaid kursusi..."):
            query_vec = embedder.encode([prompt], normalize_embeddings=True)[0]

            # compute embeddings for docs on the fly (cache could be added later)
            texts = docs_work[text_col].fillna("").astype(str).tolist()
            doc_embs = embedder.encode(texts, normalize_embeddings=True)

            scores = cosine_similarity([query_vec], doc_embs)[0]
            docs_work = docs_work.reset_index(drop=True)
            docs_work["score"] = scores

            top_k = 5
            top = docs_work.sort_values("score", ascending=False).head(top_k)

            # build context for LLM
            rows = []
            for _, r in top.iterrows():
                code = str(r[code_col]) if code_col else ""
                txt = str(r[text_col])
                rows.append(f"- {code}\n{txt}".strip())

            context_text = "\n\n".join(rows)

        # ---- 4) CALL OPENROUTER LLM ----
        headers = {}
        if site_url.strip():
            headers["HTTP-Referer"] = site_url.strip()
        if app_title.strip():
            headers["X-Title"] = app_title.strip()

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers=headers or None,
        )

        system_prompt = {
            "role": "system",
            "content": (
                "Oled Tartu Ülikooli kursusenõustaja. "
                "Kasuta allolevat kursusekonteksti (RAG top-k) ja vasta eesti keeles. "
                "Kui kontekst ei kata küsimust, ütle seda ja küsi täpsustavaid küsimusi.\n\n"
                f"KONTEKST:\n{context_text}"
            ),
        }

        messages_to_send = [system_prompt] + st.session_state.messages

        try:
            stream = client.chat.completions.create(
                model="google/gemma-3-27b-it",
                messages=messages_to_send,
                stream=True,
            )
            response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"OpenRouter viga: {e}")