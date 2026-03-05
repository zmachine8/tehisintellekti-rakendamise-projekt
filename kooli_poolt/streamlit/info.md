Et “Web API” (nt FastAPI backend) Streamlit’i chatboti ette panna, teed nii:

Streamlit UI kogub sõnumid ja hoiab st.session_state.messages ajalugu

Iga uue prompt-iga teeb HTTP POST sinu backend’i endpointi (nt /chat)

Backend tagastab JSON-i (nt { "reply": "..." }) ja UI lisab selle ajalukku

Allpool on töötav minimaalne näide.

1) Streamlit: lisa vestlusajalugu + API-kõne
import streamlit as st
import requests

st.set_page_config(page_title="Minu Esimene Äpp", page_icon="🤖")

st.title("🎓 AI Kursuse Nõustaja")
st.caption("Lihtne vestlusliides Web API kaudu.")

API_URL = "http://127.0.0.1:8000/chat"  # FastAPI endpoint

# 1) Algatame vestluse ajaloo, kui seda veel pole
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Tere! Kirjelda, mida soovid õppida."}
    ]

# 2) Kuvame vestluse senise ajaloo
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

def call_chat_api(messages):
    """
    Saadame kogu ajaloo (või viimased N sõnumit) backendile.
    Backend otsustab, kuidas seda LLM-ile anda.
    """
    payload = {"messages": messages}
    r = requests.post(API_URL, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["reply"]

# 3) Korjame üles uue kasutaja sisendi
if prompt := st.chat_input("Kirjelda, mida soovid õppida..."):
    # Kuvame kohe kasutaja sõnumi ja salvestame selle ajalukku
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Kuvame vastuse ja salvestame ajalukku
    with st.chat_message("assistant"):
        with st.spinner("Mõtlen..."):
            try:
                reply = call_chat_api(st.session_state.messages)
            except requests.RequestException as e:
                reply = f"API viga: {e}"
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})


Kui tahad saata backendile ainult viimased N sõnumit, tee:
call_chat_api(st.session_state.messages[-10:])

2) FastAPI: tee /chat endpoint (mock või LLM-iga)
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Literal

app = FastAPI()

Role = Literal["user", "assistant", "system"]

class Msg(BaseModel):
    role: Role
    content: str

class ChatRequest(BaseModel):
    messages: List[Msg]

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # MINIMAALNE: automaatvastus viimasele user sõnumile
    last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    return ChatResponse(reply=f"Sain su sõnumi: '{last_user}'. (LLM siia hiljem)")


Käivitamine:

uvicorn main:app --reload --port 8000

3) Kuidas see “õige” chatboti arhitektuurina välja näeb

Streamlit: ainult UI + session_state (kerge, ei hoia salajasi võtmeid)

Web API (FastAPI):

hoiab LLM API võtmeid / Ollama hosti seadeid

teeb RAG otsingu (vektorbaas)

koostab prompti + kutsub LLM-i

tagastab reply

4) Kui tahad “streaming” vastust (tüpib jooksvalt)

Siis muutub nii:

FastAPI peab andma SSE / chunked vastuseid

Streamlit pool peab lugema tükke ja uuendama st.empty()-ga
Kui see on su järgmine samm, ütlen täpselt milline SSE näide valida (FastAPI StreamingResponse + Streamlit requests streaming).