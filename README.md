# 🧠 IPagent Ultra-Lite

**Assistente médico com IA local — 100% gratuito, sem consumo de tokens.**

> 🔒 Seus dados nunca saem do computador. A IA roda localmente, sem APIs pagas, sem nuvem.

---

## ✨ Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| 🎙️ **Transcrição ao Vivo** | Web Speech API (navegador) com correção médica pela IA |
| 🧠 **Correção Médica** | 2 camadas: dicionário rápido + LLM para termos técnicos |
| 💬 **Chat Clínico** | Converse com a IA sobre a consulta em andamento |
| 📊 **Análise Diagnóstica** | IA analisa transcrição e sugere plano baseado em evidências |
| 📝 **Nota SOAP** | Gera notas no formato SOAP automaticamente |
| 📚 **Base de Conhecimento** | Upload de PDFs científicos para embasamento (RAG) |
| 🗝️ **API Keys** | Integração com sistemas externos via API |
| 📦 **Coleta para Fine-tuning** | Acumula correções para treinamento futuro |

### 💰 Custo de Operação: R$ 0,00

O IPagent usa **modelos de IA de código aberto** que rodam **100% no seu computador**:
- **Sem APIs pagas** (OpenAI, Google, etc.)
- **Sem consumo de tokens**
- **Sem assinaturas mensais**
- **Sem envio de dados para nuvem**
- Modelos: [Qwen 2.5](https://huggingface.co/Qwen) e [Llama 3.2](https://huggingface.co/meta-llama) (open source)

---

## 🚀 Instalação Rápida (1 comando)

### 🐧 Linux

```bash
git clone https://github.com/drpauloguimaraesjr/IPagent.git && cd IPagent && bash install.sh
```

Ou instale direto da internet:
```bash
curl -fsSL https://raw.githubusercontent.com/drpauloguimaraesjr/IPagent/main/install.sh | bash
```

### 🍎 macOS

```bash
git clone https://github.com/drpauloguimaraesjr/IPagent.git && cd IPagent && bash install.sh
```

Ou instale direto da internet:
```bash
curl -fsSL https://raw.githubusercontent.com/drpauloguimaraesjr/IPagent/main/install.sh | bash
```

> ✅ Funciona em Mac Intel e Apple Silicon (M1/M2/M3/M4) com aceleração Metal automática.

### 🪟 Windows

**Opção 1 — PowerShell (recomendado):**
```powershell
git clone https://github.com/drpauloguimaraesjr/IPagent.git; cd IPagent; .\install.ps1
```

Ou instale direto da internet:
```powershell
irm https://raw.githubusercontent.com/drpauloguimaraesjr/IPagent/main/install.ps1 | iex
```

**Opção 2 — Prompt de Comando (CMD):**
```cmd
git clone https://github.com/drpauloguimaraesjr/IPagent.git && cd IPagent && install.bat
```

> 💡 Se Python não estiver instalado, o instalador tenta instalar automaticamente via `winget`.

---

## ▶️ Como Executar

Após a instalação, basta:

| Sistema | Comando |
|---------|---------|
| Linux / macOS | `./run.sh` |
| Windows (PowerShell) | `.\run.ps1` |
| Windows (CMD) | `run.bat` |

Ou manualmente:
```bash
# Linux / macOS
source venv/bin/activate
python main.py

# Windows
venv\Scripts\activate
python main.py
```

Acesse: **http://localhost:5000**

Na 1ª execução, o modelo de IA (~2 GB) é baixado automaticamente. Depois, inicia em segundos.

---

## 📦 Requisitos

### Mínimos
- **Python 3.10+**
- **4 GB de RAM** (modelo 3B na CPU)
- **~3 GB de disco** (código + modelo)

### Recomendados
- **8 GB de RAM**
- **GPU NVIDIA com 4+ GB VRAM** (Linux/Windows) ou **Apple Silicon** (macOS)
- **~3 GB de disco**

### O que o instalador configura automaticamente
- ✅ Python (se não tiver)
- ✅ Git (se não tiver)
- ✅ Ambiente virtual (venv)
- ✅ Todas as dependências pip
- ✅ Detecção de GPU (NVIDIA CUDA / Apple Metal)
- ✅ Compilação otimizada para sua GPU
- ✅ Scripts de execução (`run.sh` / `run.bat` / `run.ps1`)
- ✅ Ollama (opcional, se desejar)

---

## 🧠 Modelos Disponíveis

| Modelo | Tamanho | RAM/VRAM | Qualidade |
|---|---|---|---|
| **`qwen2.5-3b`** (padrão) | 1.9 GB | ~3 GB | Boa |
| `qwen2.5-7b` | 4.7 GB | ~5 GB | Muito boa |
| `llama3.2-3b` | 2.0 GB | ~3 GB | Boa |

Para trocar o modelo:
```bash
IPAGENT_MODEL=qwen2.5-7b python main.py
```

---

## 🔌 Ollama (Opcional)

O IPagent funciona **sem Ollama** por padrão — a IA roda embutida via `llama-cpp-python`.

Se preferir usar Ollama (servidor de IA separado, mais modelos disponíveis):

```bash
# O instalador pergunta se deseja instalar Ollama
# Ou instale manualmente:
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b

# Execute o IPagent apontando para Ollama:
IPAGENT_OLLAMA_HOST=http://localhost:11434 python main.py
```

### Embutido vs Ollama

| Aspecto | Embutido (padrão) | Com Ollama |
|---|---|---|
| Instalação | Mais simples | Precisa instalar Ollama |
| Performance | Boa | Pode ser melhor (otimizado) |
| Modelos | 3 pré-configurados | Centenas disponíveis |
| Gestão | Automática | Via `ollama` CLI |
| Custo | R$ 0,00 | R$ 0,00 |

---

## ⚙️ Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `IPAGENT_MODEL` | `qwen2.5-3b` | Modelo de IA |
| `IPAGENT_GPU_LAYERS` | `-1` (auto) | `-1` = toda GPU, `0` = só CPU |
| `IPAGENT_PORT` | `5000` | Porta do servidor |
| `IPAGENT_CORRECTION_ENABLED` | `true` | Correção médica ativa |
| `IPAGENT_OLLAMA_HOST` | — | URL do Ollama (se usar) |

---

## 📁 Estrutura

```
IPagent/
├── install.sh               # Instalador Linux/macOS
├── install.bat               # Instalador Windows (CMD)
├── install.ps1               # Instalador Windows (PowerShell)
├── run.sh                    # Executar (Linux/macOS)
├── run.bat                   # Executar (Windows CMD)
├── run.ps1                   # Executar (Windows PowerShell)
├── main.py                   # Ponto de entrada
├── config.py                 # Configurações
├── requirements.txt          # Dependências (7 pacotes)
├── core/
│   ├── agent.py              # LLM + RAG + Correção Médica
│   ├── memory.py             # SQLite FTS5 (base de conhecimento)
│   ├── model_manager.py      # Download e carregamento do modelo
│   ├── audio.py              # Processamento de áudio
│   └── transcriber.py        # Motor de transcrição
├── training/
│   ├── data_collector.py     # Coleta dados para fine-tuning
│   └── fine_tuner.py         # Pipeline de fine-tuning
├── web/
│   ├── app.py                # Rotas Flask
│   └── templates/
│       ├── index.html        # Interface principal (dark mode)
│       ├── admin.html        # Painel de API Keys
│       └── knowledge.html    # Base de Conhecimento
├── Dockerfile                # Build Docker
└── docker-compose.yml        # Docker Compose (com Ollama)
```

---

## 🐳 Docker (alternativa)

```bash
# Sem GPU
docker build -t ipagent .
docker run -p 5000:5000 ipagent

# Com GPU + Ollama
docker-compose up -d
```

---

## 🔒 Privacidade e Segurança

- **Nenhum dado sai do seu computador** — tudo roda localmente
- **Sem telemetria** — não enviamos nenhuma informação
- **Código aberto** — você pode auditar cada linha
- **Modelos open source** — Qwen (Alibaba) e Llama (Meta), licenças permissivas

---

## 📄 Licença

Projeto em desenvolvimento — Dr. Paulo Guimarães Jr.
