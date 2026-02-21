import streamlit as st
import requests

st.set_page_config(page_title="AI Kursuse Nõustaja", page_icon="🎓")
st.title("🎓 AI Kursuse Nõustaja")

API_URL = "http://127.0.0.1:8000/chat"

# 1) Algatame vestluse ajaloo, kui seda veel pole
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "Sa oled Tartu Ülikooli kursuse nõustaja. Vasta eesti keeles."},
        {"role": "assistant", "content": "Kirjelda, mida soovid õppida (nt teema, tase, eesmärk)."},
    ]

# 2) Kuvame vestluse senise ajaloo
for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

def call_api(messages):
    r = requests.post(API_URL, json={"messages": messages}, timeout=60)
    r.raise_for_status()
    return r.json()["reply"]

# 3) Korjame üles uue kasutaja sisendi
if prompt := st.chat_input("Kirjelda, mida soovid õppida..."):
    # user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # assistant reply
    with st.chat_message("assistant"):
        with st.spinner("Mõtlen..."):
            try:
                reply = call_api(st.session_state.messages)
            except requests.RequestException as e:
                reply = f"API viga: {e}"
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
