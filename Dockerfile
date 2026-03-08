FROM python:3.11-slim

WORKDIR /app

# Dependências mínimas do sistema para llama-cpp-python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretórios de dados
RUN mkdir -p data/models data/knowledge data/consultations data/training_datasets data/uploads

# O modelo será baixado automaticamente na primeira execução
# Ou monte um volume com o modelo pré-baixado:
# docker run -v /caminho/modelo:/app/data/models ipagent

EXPOSE 5000

# Variáveis de ambiente opcionais
ENV IPAGENT_MODEL=qwen2.5-3b
ENV IPAGENT_GPU_LAYERS=0

CMD ["python", "main.py"]
