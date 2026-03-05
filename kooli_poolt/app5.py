import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# pealkiri
st.title("🎓 AI Kursuse Nõustaja - Samm 5")
st.caption("RAG süsteem koos eel-filtreerimisega.")

# külgriba
with st.sidebar:
    api_key = st.text_input("OpenRouter API Key", type="password")
    st.info("Selles versioonis saad filtreerida metaandmete järgi enne semantilist otsingut.")

@st.cache_resource
def get_models():
    base = Path(__file__).parent
    embedder = SentenceTransformer("BAAI/bge-m3")
    df = pd.read_csv(base / "puhtad_andmed.csv")
    embeddings_df = pd.read_pickle(base / "puhtad_andmed_embeddings.pkl")
    if "embedding" in embeddings_df.columns:
        embeddings_df["embedding"] = embeddings_df["embedding"].apply(
            lambda x: np.array(x, dtype=np.float32)
        )
    return embedder, df, embeddings_df

embedder, df, embeddings_df = get_models()

# --- Metaandmete filtrid UI-s (külgribal) ---
with st.sidebar:
    # turvaliselt valikute tegemine ainult siis, kui veerud olemas
    semester_val = None
    eap_val = None

    if "semester" in df.columns:
        sem_opts = ["(kõik)"] + sorted([str(x) for x in df["semester"].dropna().unique().tolist()])
        semester_val = st.selectbox("Semester", sem_opts, index=0)

    if "eap" in df.columns:
        eap_opts = ["(kõik)"] + sorted([str(x) for x in df["eap"].dropna().unique().tolist()], key=lambda x: float(x) if x != "(kõik)" else -1)
        eap_val = st.selectbox("EAP", eap_opts, index=0)

# 1. alustame
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. kuvame ajaloo
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. kuulame kasutaja sõnumit
if prompt := st.chat_input("Kirjelda, mida soovid õppida..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key:
            error_msg = "Palun sisesta API võti!"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        else:
            with st.spinner("Otsin sobivaid kursusi..."):
                merged_df = pd.merge(df, embeddings_df, on="unique_ID", how="inner")

                # 1) Metaandmete filter enne semantilist otsingut
                mask = pd.Series(True, index=merged_df.index)

                if semester_val and semester_val != "(kõik)" and "semester" in merged_df.columns:
                    mask &= (merged_df["semester"].astype(str) == str(semester_val))

                if eap_val and eap_val != "(kõik)" and "eap" in merged_df.columns:
                    # hoia tüübid kooskõlas
                    mask &= (merged_df["eap"].astype(str) == str(eap_val))

                filtered_df = merged_df[mask].copy()

                if filtered_df.empty:
                    st.warning("Ühtegi kursust ei vasta filtritele.")
                    context_text = "Sobivaid kursusi ei leitud (metaandmete filter andis 0 tulemust)."
                else:
                    # 2) Semantiline otsing filtritud hulgas
                    query_vec = embedder.encode([prompt])[0]
                    emb_matrix = np.stack(filtered_df["embedding"].values)
                    filtered_df["score"] = cosine_similarity([query_vec], emb_matrix)[0]

                    # Top N
                    return_N = 5
                    results_df = filtered_df.sort_values("score", ascending=False).head(return_N).copy()

                    # puhastame ära
                    results_df.drop(columns=[c for c in ["score", "embedding"] if c in results_df.columns],
                                   inplace=True, errors="ignore")

                    context_text = results_df.to_string(index=False)

            # 3) LLM vastus
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            system_prompt = {
                "role": "system",
                "content": (
                    "Oled nõustaja. Kasuta järgmisi kursusi vastamiseks (metaandmete järgi filtritud + semantiliselt leitud):\n\n"
                    f"{context_text}"
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
                st.error(f"Viga: {e}")