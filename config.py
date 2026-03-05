"""
Configurações centralizadas do IPagent.
Todas as configurações ajustáveis do sistema estão aqui.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# Diretório base do projeto
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
CONSULTATIONS_DIR = DATA_DIR / "consultations"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
TRAINING_DIR = DATA_DIR / "training_datasets"


@dataclass
class TranscriberConfig:
    """Configurações do motor de transcrição (faster-whisper)."""
    
    # Modelo Whisper: tiny, base, small, medium, large-v3
    # Para RTX 4060 8GB, recomendado: "medium" para pt-BR
    model_size: str = "medium"
    
    # Dispositivo: "cuda" para GPU, "cpu" para CPU
    device: str = "cuda"
    
    # Tipo de computação: "float16" para GPU, "int8" para CPU
    compute_type: str = "float16"
    
    # Idioma principal (pt = português)
    language: str = "pt"
    
    # Beam size para decodificação (maior = mais preciso, mais lento)
    beam_size: int = 5
    
    # Tamanho do chunk de áudio em segundos
    chunk_duration: float = 2.0
    
    # Usar VAD (Voice Activity Detection) para filtrar silêncio
    use_vad: bool = True
    
    # Limiar de probabilidade de fala para VAD
    vad_threshold: float = 0.5


@dataclass
class AudioConfig:
    """Configurações de captura de áudio."""
    
    # Taxa de amostragem (Hz) - Whisper espera 16000
    sample_rate: int = 16000
    
    # Canais de áudio (1 = mono, 2 = estéreo)
    channels: int = 1
    
    # Tamanho do bloco de áudio
    block_size: int = 1024
    
    # Duração do buffer circular em segundos
    buffer_duration: float = 30.0
    
    # Dispositivo de áudio (None = padrão do sistema)
    device_index: Optional[int] = None


@dataclass
class AgentConfig:
    """Configurações do agente LLM (Ollama)."""
    
    # URL do servidor Ollama
    ollama_host: str = "http://localhost:11434"
    
    # Modelo padrão - opções recomendadas para 8GB VRAM:
    # - "qwen2.5:7b-instruct-q4_K_M" (melhor qualidade)
    # - "llama3.2:3b" (mais rápido)
    # - "mistral:7b-instruct-q4_K_M" (bom equilíbrio)
    model_name: str = "qwen2.5:7b-instruct-q4_K_M"
    
    # Temperatura para geração (0.0 = determinístico, 1.0 = criativo)
    temperature: float = 0.3
    
    # Contexto máximo em tokens
    max_context: int = 8192
    
    # Prompt do sistema para o assistente médico
    system_prompt: str = """Você é um assistente médico inteligente chamado IPagent.
Sua função é auxiliar o profissional de saúde durante consultas médicas.

Suas capacidades incluem:
1. Analisar transcrições de consultas em tempo real
2. Sugerir diagnósticos diferenciais baseados nos sintomas relatados
3. Lembrar informações relevantes do histórico do paciente
4. Gerar resumos estruturados da consulta (formato SOAP)
5. Alertar sobre possíveis interações medicamentosas
6. Sugerir exames complementares quando apropriado

IMPORTANTE:
- Você é um AUXILIAR. Todas as decisões clínicas são do profissional.
- Nunca faça diagnósticos definitivos.
- Sempre priorize a segurança do paciente.
- Respostas devem ser claras, concisas e em português.
- Use terminologia médica profissional quando apropriado.
"""


@dataclass
class MemoryConfig:
    """Configurações da base de conhecimento (ChromaDB)."""
    
    # Diretório de persistência do ChromaDB
    persist_directory: str = str(KNOWLEDGE_DIR / "chromadb")
    
    # Nome da coleção principal
    collection_name: str = "medical_knowledge"
    
    # Modelo de embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Número máximo de resultados RAG
    max_results: int = 5
    
    # Limiar de similaridade mínimo
    similarity_threshold: float = 0.7


@dataclass
class TrainingConfig:
    """Configurações de fine-tuning."""
    
    # Modelo base para fine-tuning
    base_model: str = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
    
    # Rank do LoRA (maior = mais capacidade, mais VRAM)
    lora_rank: int = 16
    
    # Alpha do LoRA
    lora_alpha: int = 16
    
    # Dropout do LoRA
    lora_dropout: float = 0.0
    
    # Taxa de aprendizado
    learning_rate: float = 2e-4
    
    # Número de épocas
    num_epochs: int = 3
    
    # Tamanho do batch
    batch_size: int = 2
    
    # Gradiente acumulado
    gradient_accumulation_steps: int = 4
    
    # Tamanho máximo de sequência
    max_seq_length: int = 2048
    
    # Diretório de saída para modelos fine-tuned
    output_dir: str = str(MODELS_DIR / "fine_tuned")
    
    # Mínimo de exemplos para iniciar fine-tuning
    min_training_samples: int = 50
    
    # Diretório com datasets de treinamento
    datasets_dir: str = str(TRAINING_DIR)


@dataclass
class WebConfig:
    """Configurações do servidor web."""
    
    # Host e porta
    host: str = "0.0.0.0"
    port: int = 5000
    
    # Modo debug
    debug: bool = True
    
    # Secret key para sessões Flask
    secret_key: str = "ipagent-secret-key-change-me"


@dataclass
class AppConfig:
    """Configuração principal que agrupa todas as sub-configurações."""
    
    transcriber: TranscriberConfig = field(default_factory=TranscriberConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    web: WebConfig = field(default_factory=WebConfig)


def load_config() -> AppConfig:
    """Carrega configuração, com override de variáveis de ambiente."""
    config = AppConfig()
    
    # Override por variáveis de ambiente
    if os.environ.get("IPAGENT_WHISPER_MODEL"):
        config.transcriber.model_size = os.environ["IPAGENT_WHISPER_MODEL"]
    
    if os.environ.get("IPAGENT_WHISPER_DEVICE"):
        config.transcriber.device = os.environ["IPAGENT_WHISPER_DEVICE"]
    
    if os.environ.get("IPAGENT_LLM_MODEL"):
        config.agent.model_name = os.environ["IPAGENT_LLM_MODEL"]
    
    if os.environ.get("IPAGENT_OLLAMA_HOST"):
        config.agent.ollama_host = os.environ["IPAGENT_OLLAMA_HOST"]
    
    if os.environ.get("IPAGENT_PORT"):
        config.web.port = int(os.environ["IPAGENT_PORT"])
    
    # Criar diretórios necessários
    for dir_path in [DATA_DIR, MODELS_DIR, CONSULTATIONS_DIR, KNOWLEDGE_DIR, TRAINING_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return config
