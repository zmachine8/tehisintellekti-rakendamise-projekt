import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Pealkirjad
st.title("🎓 AI Kursuse Nõustaja - RAGiga")
st.caption("Täisväärtuslik RAG süsteem semantilise otsinguga.")

# Külgriba
with st.sidebar:
    api_key = st.text_input("OpenRouter API Key", type="password")
    st.info("Embedder: BAAI/bge-m3 | LLM: google/gemma-3-27b-it")

# Mudeli, andmetabeli ja vektoriseeritud andmete laadimine
# Eeldame, et puhtad_andmed_embeddings.pkl on pd.DataFrame veergudega (unique_ID, embedding)
@st.cache_resource
def get_models():
    base = Path(__file__).parent
    df = pd.read_csv(base / "puhtad_andmed.csv")
    embeddings_df = pd.read_pickle(base / "puhtad_andmed_embeddings.pkl")

    embedder = SentenceTransformer("BAAI/bge-m3")

    # tee kindlaks, et embedding on numpy array
    # (mõnikord võib olla list)
    if "embedding" in embeddings_df.columns:
        embeddings_df["embedding"] = embeddings_df["embedding"].apply(
            lambda x: np.array(x, dtype=np.float32)
        )

    return embedder, df, embeddings_df

embedder, df, embeddings_df = get_models()

# 1. Algatame vestluse ajaloo, kui seda veel pole
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Kuvame vestluse senise ajaloo (History)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Korjame üles kasutaja sõnumi
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
            # Semantiline otsing (RAG)
            with st.spinner("Otsin sobivaid kursusi..."):
                # Query embedding
                query_vec = embedder.encode([prompt])[0]

                # Ühendame csv + embeddings
                merged_df = pd.merge(df, embeddings_df, on="unique_ID", how="inner")

                if merged_df.empty:
                    context_text = "Sobivaid kursusi ei leitud (andmete ühendamine ebaõnnestus)."
                else:
                    # Cosine similarity: vaja 2D maatriksit embeddings'itest
                    emb_matrix = np.stack(merged_df["embedding"].values)
                    merged_df["score"] = cosine_similarity([query_vec], emb_matrix)[0]

                    # Top N
                    results_N = 5
                    results_df = merged_df.sort_values("score", ascending=False).head(results_N).copy()

                    # eemaldame ebavajalikud veerud
                    drop_cols = [c for c in ["score", "embedding", "unique_ID"] if c in results_df.columns]
                    results_df.drop(columns=drop_cols, inplace=True, errors="ignore")

                    context_text = results_df.to_string(index=False)

            # LLM vastus koos kontekstiga
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            system_prompt = {
                "role": "system",
                "content": (
                    "Oled nõustaja. Kasuta järgmisi RAGi leitud kursusi vastamiseks. "
                    "Kui kontekst ei sobi küsimusega, ütle seda selgelt.\n\n"
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