# 🧠 IPagent Ultra-Lite

**Assistente médico com IA local — sem Ollama, sem dependências externas.**

Apenas `pip install` e `python main.py`. O modelo de IA baixa automaticamente na primeira execução.

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

## 🚀 Instalação (3 passos)

```bash
# 1. Clonar o projeto
git clone https://github.com/seu-usuario/IPagent.git
cd IPagent

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar!
python main.py
# Na 1ª vez, o modelo de IA (~2 GB) será baixado automaticamente.
# Depois disso, inicia em segundos.
```

Acesse: **http://localhost:5000**

**Não precisa instalar Ollama nem nenhum outro programa.**

## 📦 Requisitos

### Mínimos
- **Python 3.10+**
- **4 GB de RAM** (modelo 3B na CPU)
- **~3 GB de disco** (código + modelo)

### Recomendados
- **8 GB de RAM**
- **GPU NVIDIA com 4+ GB VRAM** (muito mais rápido)
- **~3 GB de disco**

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

## ⚙️ Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `IPAGENT_MODEL` | `qwen2.5-3b` | Modelo de IA |
| `IPAGENT_GPU_LAYERS` | `-1` (auto) | `-1` = toda GPU, `0` = só CPU |
| `IPAGENT_PORT` | `5000` | Porta do servidor |
| `IPAGENT_CORRECTION_ENABLED` | `true` | Correção médica ativa |

## 📁 Estrutura

```
IPagent/
├── main.py                  # Ponto de entrada
├── config.py                # Configurações
├── requirements.txt         # 7 dependências
├── core/
│   ├── agent.py             # LLM + RAG + Correção Médica
│   ├── memory.py            # SQLite FTS5 (base de conhecimento)
│   └── model_manager.py     # Download e carregamento do modelo
├── training/
│   ├── data_collector.py    # Coleta dados para fine-tuning
│   └── fine_tuner.py        # Pipeline de fine-tuning (opcional)
└── web/
    ├── app.py               # Rotas Flask
    └── templates/
        ├── index.html       # Interface principal (dark mode)
        └── admin.html       # Painel de API Keys
```

## 🐳 Docker

```bash
docker build -t ipagent .
docker run -p 5000:5000 ipagent
```

## 📄 Licença

Projeto em desenvolvimento — Dr. Paulo Guimarães Jr.
