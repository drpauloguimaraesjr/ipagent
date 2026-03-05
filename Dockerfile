FROM python:3.10-slim

# Instalar dependências de sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    alsa-utils \
    portaudio19-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências Python primeiro (aproveita o cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do IPagent
COPY . .

# Expor porta da Web Interface
EXPOSE 5000

# Variáveis de ambiente
ENV IPAGENT_PORT=5000
ENV IPAGENT_OLLAMA_HOST="http://ollama:11434"

# Comando para rodar a aplicação
CMD ["python", "main.py"]
