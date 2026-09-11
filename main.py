from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
import openai
import os

app = FastAPI()
security = HTTPBasic()

# CORS para Streamlit Cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Usuários (ajuste as senhas!)
USERS = {
    "admin": os.getenv("ADMIN_PASSWORD", "admin123"),
    "user1": os.getenv("USER1_PASSWORD", "verint2024"),
    "user2": os.getenv("USER2_PASSWORD", "verint2024"),
    "user3": os.getenv("USER3_PASSWORD", "verint2024"),
    "user4": os.getenv("USER4_PASSWORD", "verint2024"),
    "user5": os.getenv("USER5_PASSWORD", "verint2024"),
    "user6": os.getenv("USER6_PASSWORD", "verint2024"),
    "user7": os.getenv("USER7_PASSWORD", "verint2024"),
    "user8": os.getenv("USER8_PASSWORD", "verint2024"),
    "user9": os.getenv("USER9_PASSWORD", "verint2024"),
    "user10": os.getenv("USER10_PASSWORD", "verint2024"),
}

# Inicializa componentes
print("📥 Carregando banco de dados...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection("verint_docs")
embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print(f"✅ {collection.count()} documentos carregados!")

openai.api_key = os.getenv("OPENAI_API_KEY")

class Question(BaseModel):
    question: str
    language: str = "pt"

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if USERS.get(credentials.username) != credentials.password:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return credentials.username

@app.get("/health")
async def health():
    return {"status": "ok", "documents": collection.count()}

@app.post("/ask")
async def ask(q: Question, username: str = Depends(verify_auth)):
    # Busca
    query_embed = embedder.encode(q.question).tolist()
    results = collection.query(
        query_embeddings=[query_embed],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )
    
    # Monta contexto
    context = "\n\n".join([
        f"[{meta['filename']} - Pág {meta['page']}]\n{doc}"
        for doc, meta in zip(results['documents'][0], results['metadatas'][0])
    ])
    
    # Chama OpenAI
    prompt = f"""Baseado apenas nestes documentos, responda em {q.language}:

{context}

Pergunta: {q.question}

Resposta:"""
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    return {
        "answer": response.choices[0].message.content,
        "sources": [
            {
                "filename": meta['filename'],
                "page": meta['page'],
                "relevance": round(1 - dist, 3)
            }
            for meta, dist in zip(results['metadatas'][0], results['distances'][0])
        ]
    }