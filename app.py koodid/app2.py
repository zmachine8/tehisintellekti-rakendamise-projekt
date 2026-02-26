import streamlit as st
from openai import OpenAI

# Iluasjad: pealkiri, allkiri
st.title("🎓 AI Kursuse Nõustaja - Samm 2")
st.caption("Vestlus päris tehisintellektiga (Gemma 3).")

# Külgriba API võtme jaoks (sidebar)
with st.sidebar:
    api_key = st.text_input("OpenRouter API Key", type="password")
    st.info("Mudel: google/gemma-3-27b-it (OpenRouter)")

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
    # kuvame kohe kasutaja sõnumi
    with st.chat_message("user"):
        st.markdown(prompt)

    # genereerime vastuse (stream)
    with st.chat_message("assistant"):
        if not api_key:
            error_msg = "Palun sisesta API võti külgribale!"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        else:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

            sys_prompt = "Oled abivalmis Tartu Ülikooli akadeemiline nõustaja. Vasta eesti keeles."
            system_prompt = {"role": "system", "content": sys_prompt}

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