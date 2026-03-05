# 🤖 IPagent — Assistente IA Local para Consultas Médicas

## Visão Geral

IPagent é um assistente de inteligência artificial que roda **100% localmente** no seu computador, projetado para auxiliar profissionais de saúde durante consultas médicas. Ele transcreve conversas em tempo real e fornece insights inteligentes.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Interface Web (Flask)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Transcrição  │  │  Chat IA     │  │  Histórico    │  │
│  │  em Tempo Real│  │  Assistente  │  │  Consultas    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
├─────────┼─────────────────┼───────────────────┼──────────┤
│         ▼                 ▼                   ▼          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │faster-whisper│  │  Ollama LLM  │  │   ChromaDB    │  │
│  │  (STT Local) │  │ (Llama/Qwen) │  │    (RAG)      │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │        Pipeline de Fine-Tuning (unsloth+QLoRA)    │   │
│  │  Consultas → Feedback → Treinamento → Modelo ↻   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Função |
|---|---|---|
| Transcrição | `faster-whisper` | Fala → Texto em tempo real |
| LLM Local | `Ollama` (Qwen 2.5 / Llama 3.2) | Cérebro do agente |
| Fine-Tuning | `unsloth` + QLoRA | Aprendizado progressivo |
| Base de Conhecimento | `ChromaDB` | Memória persistente (RAG) |
| Interface | `Flask` + WebSocket | UI para consultas |
| Áudio | `sounddevice` + `webrtcvad` | Captura de microfone |

## 📋 Requisitos de Hardware

- **GPU**: NVIDIA RTX 4060 8GB (ou superior)
- **RAM**: 16GB+ recomendado
- **Armazenamento**: 20GB+ para modelos
- **Microfone**: Qualquer microfone USB/integrado

## 🚀 Instalação

```bash
# 1. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 4. Baixar modelo LLM
ollama pull qwen2.5:7b-instruct-q4_K_M

# 5. Baixar modelo de transcrição (automático no primeiro uso)
# O faster-whisper baixa o modelo automaticamente

# 6. Iniciar o IPagent
python main.py
```

## 📁 Estrutura do Projeto

```
IPagent/
├── main.py                 # Ponto de entrada principal
├── requirements.txt        # Dependências Python
├── config.py               # Configurações do sistema
├── core/
│   ├── __init__.py
│   ├── transcriber.py      # Motor de transcrição (faster-whisper)
│   ├── agent.py            # Agente LLM (Ollama)
│   ├── memory.py           # Base de conhecimento (ChromaDB/RAG)
│   └── audio.py            # Captura de áudio em tempo real
├── training/
│   ├── __init__.py
│   ├── data_collector.py   # Coleta dados para fine-tuning
│   ├── fine_tuner.py       # Pipeline de fine-tuning (unsloth)
│   └── datasets/           # Dados de treinamento
├── web/
│   ├── __init__.py
│   ├── app.py              # Servidor Flask
│   ├── templates/
│   │   └── index.html      # Interface principal
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
└── data/
    ├── consultations/      # Transcrições salvas
    ├── models/             # Modelos fine-tuned
    └── knowledge/          # Base de conhecimento
```

## 🔄 Ciclo de Aprendizado Progressivo

1. **Transcreve** consultas em tempo real
2. **Armazena** transcrições + feedback do médico
3. **Coleta** dados formatados para treinamento
4. **Fine-tuna** o modelo com QLoRA (periódico)
5. **Melhora** a cada ciclo — vocabulário médico, padrões, sugestões

## 🔒 Privacidade

- ✅ Tudo roda **localmente** — nenhum dado sai do seu computador
- ✅ Sem APIs externas — sem custos de uso
- ✅ Compatível com requisitos de sigilo médico
