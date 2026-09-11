from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
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

# Usuários configurados
USERS = {
    "admin": os.getenv("ADMIN_PASSWORD", "Wttw@9919910630"),
    "bruno.felix": os.getenv("USER_BRUNO_PASSWORD", "Wittel01"),
    "adelson.ferreira": os.getenv("USER_ADELSON_PASSWORD", "Wittel01"),
    "joselino.junior": os.getenv("USER_JOSELINO_PASSWORD", "Wittel01"),
    "paulo.avelar": os.getenv("USER_PAULO_PASSWORD", "Wittel01"),
    "rogerio.fernandes": os.getenv("USER_ROGERIO_PASSWORD", "Wittel01"),
}

# Inicializa OpenAI (nova API)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Inicializa componentes
print("📥 Carregando banco de dados...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
try:
    collection = chroma_client.get_collection("verint_docs")
    print(f"✅ {collection.count()} documentos carregados!")
except:
    print("⚠️ Coleção não encontrada. Criando vazia...")
    collection = chroma_client.create_collection("verint_docs")
    print("✅ Coleção criada. Faça upload do banco.")

print("🧠 Carregando modelo de embeddings...")
embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("✅ Modelo carregado!")

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
    
    # Se não houver resultados
    if not results['documents'][0]:
        return {
            "answer": "Não encontrei informações relevantes nos documentos.",
            "sources": [],
            "confidence": "baixa"
        }
    
    # Monta contexto
    context = "\n\n".join([
        f"[{meta['filename']} - Pág {meta['page']}]\n{doc}"
        for doc, meta in zip(results['documents'][0], results['metadatas'][0])
    ])
    
    # Chama OpenAI (NOVA API)
    prompt = f"""Baseado apenas nestes documentos, responda em {q.language}:

{context}

Pergunta: {q.question}

Resposta:"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )
        
        answer = response.choices[0].message.content
        
        return {
            "answer": answer,
            "sources": [
                {
                    "filename": meta['filename'],
                    "page": meta['page'],
                    "relevance": round(1 - dist, 3)
                }
                for meta, dist in zip(results['metadatas'][0], results['distances'][0])
            ],
            "confidence": "alta"
        }
        
    except Exception as e:
        print(f"Erro OpenAI: {e}")
        return {
            "answer": f"Erro ao gerar resposta: {str(e)}",
            "sources": [],
            "confidence": "erro"
        }

# ========== ENDPOINT DE IMPORTAÇÃO (NO FINAL DO ARQUIVO) ==========
@app.post("/import")
async def import_data(data: dict, username: str = Depends(verify_auth)):
    """
    Recebe dados em formato JSON e insere no ChromaDB
    """
    try:
        documents = data.get('documents', [])
        embeddings = data.get('embeddings', [])
        metadatas = data.get('metadatas', [])
        ids = data.get('ids', [])
        
        if not documents:
            return {"status": "error", "message": "No documents provided"}
        
        # Insere no ChromaDB
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        return {
            "status": "success",
            "inserted": len(documents),
            "total": collection.count()
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}