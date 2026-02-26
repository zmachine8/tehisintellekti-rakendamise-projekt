import streamlit as st
import pandas as pd
from pathlib import Path
from openai import OpenAI

st.title("🎓 AI Kursuse Nõustaja")
st.caption("AI kasutab kursuste andmeid (esimesed 10 rida).")

# Külgriba API võtme jaoks
with st.sidebar:
    api_key = st.text_input("OpenRouter API Key", type="password")
    st.info("Mudel: google/gemma-3-27b-it (OpenRouter)")

# Laeme andmed (puhtad_andmed.csv peab olema õiges asukohas)
# Kasuta cache'i, et ei loetaks iga refreshiga uuesti
@st.cache_data
def load_data():
    base = Path(__file__).parent
    csv_path = base / "puhtad_andmed.csv"
    df = pd.read_csv(csv_path)
    return df

df = load_data()

# 1. Algatame vestluse ajaloo, kui seda veel pole
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Kuvame vestluse senise ajaloo (History)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Korjame üles uue kasutaja sisendi
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
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

            # Võtame 10 esimest rida ja teeme sellest konteksti
            head_df = df.head(10)
            context_text = head_df.to_string(index=False)

            system_prompt = {
                "role": "system",
                "content": (
                    "Oled abivalmis Tartu Ülikooli akadeemiline nõustaja. "
                    "Sul on allpool kursuste andmete väljavõte (10 esimest rida). "
                    "Kasuta seda infot vastamiseks, kui see on asjakohane. "
                    "Vasta eesti keeles.\n\n"
                    f"KURSUSTE ANDMED (10 rida):\n{context_text}"
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

# TODO TESTi brauseris: "tere anna mulle kõigi kursuste nimed, mida sa tead"