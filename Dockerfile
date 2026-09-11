FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema (com retry)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o banco de dados e código
COPY chroma_db/ ./chroma_db/
COPY main.py .

ENV CHROMA_DB_PATH=./chroma_db
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]