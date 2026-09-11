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