import os
from getpass import getpass
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional
from openai import OpenAI

app = FastAPI()

Role = Literal["system", "user", "assistant"]

class Msg(BaseModel):
    role: Role
    content: str

class ChatRequest(BaseModel):
    messages: List[Msg]
    model: Optional[str] = None

# hoitakse ainult protsessi mälus
CLIENT: Optional[OpenAI] = None

def get_client() -> OpenAI:
    global CLIENT
    if CLIENT is not None:
        return CLIENT

    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        key = getpass("OpenRouter API key: ").strip()
        if not key:
            raise RuntimeError("API key puudub")

    CLIENT = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "AI Kursuse Nõustaja",
        },
    )
    return CLIENT

@app.post("/chat")
def chat(req: ChatRequest):
    client = get_client()
    model = req.model or "openai/gpt-4o-mini"
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[m.model_dump() for m in req.messages],
            temperature=0.4,
        )
        return {"reply": completion.choices[0].message.content or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#uvicorn streamlit_host:app --reload --port 8000
# küsib: OpenRouter API key: ******
