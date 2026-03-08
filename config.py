"""
Configurações centralizadas do IPagent Ultra-Lite.
Sem Ollama — IA roda direto no Python.
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
class AgentConfig:
    """Configurações do agente LLM (llama-cpp-python direto)."""

    # Nome do modelo (ver core/model_manager.py para lista)
    # Opções: "qwen2.5-3b", "qwen2.5-7b", "llama3.2-3b"
    model_name: str = "qwen2.5-3b"

    # Diretório onde ficam os arquivos .gguf
    models_dir: str = str(MODELS_DIR)

    # GPU: -1 = usa toda GPU disponível, 0 = só CPU
    n_gpu_layers: int = -1

    # Contexto máximo em tokens (None = usa o padrão do modelo)
    n_ctx: Optional[int] = None

    # Temperatura para geração (0.0 = determinístico, 1.0 = criativo)
    temperature: float = 0.3

    # Máximo de tokens na resposta
    max_tokens: int = 2048


@dataclass
class MemoryConfig:
    """Configurações da base de conhecimento (SQLite FTS5)."""

    # Arquivo do banco de dados SQLite
    db_path: str = str(KNOWLEDGE_DIR / "knowledge.db")

    # Número máximo de resultados na busca
    max_results: int = 5


@dataclass
class TrainingConfig:
    """Configurações de coleta de dados para fine-tuning."""

    # Modelo base para fine-tuning (quando for usar)
    base_model: str = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"

    # LoRA configs
    lora_rank: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    learning_rate: float = 2e-4
    num_epochs: int = 3
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048

    # Diretórios
    output_dir: str = str(MODELS_DIR / "fine_tuned")
    datasets_dir: str = str(TRAINING_DIR)

    # Mínimo de exemplos para iniciar fine-tuning
    min_training_samples: int = 50


@dataclass
class CorrectionConfig:
    """Configurações da camada de correção médica da transcrição."""

    # Ativar correção automática via LLM
    enabled: bool = True

    # Número mínimo de palavras para acionar a correção
    min_words_to_correct: int = 3

    # Dicionário de termos médicos comuns para validação rápida
    quick_corrections: dict = None

    def __post_init__(self):
        if self.quick_corrections is None:
            self.quick_corrections = {
                "disney": "dispneia",
                "Disney": "dispneia",
                "taqui cardia": "taquicardia",
                "bradi cardia": "bradicardia",
                "fibrilação a trial": "fibrilação atrial",
                "hiper tensão": "hipertensão",
                "hipo tensão": "hipotensão",
                "cetri axona": "ceftriaxona",
                "amoxi cilina": "amoxicilina",
                "anti biótico": "antibiótico",
                "hemoglobina gli cada": "hemoglobina glicada",
                "eletro cardiograma": "eletrocardiograma",
                "tomo grafia": "tomografia",
                "resso nância": "ressonância",
                "ultra som": "ultrassom",
                "pressão alta": "hipertensão arterial",
                "açúcar no sangue": "glicemia",
                "ataque cardíaco": "infarto agudo do miocárdio",
                "derrame": "acidente vascular cerebral",
            }


@dataclass
class WebConfig:
    """Configurações do servidor web."""

    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = True
    secret_key: str = "ipagent-secret-key-change-me"

    # HTTPS (necessário para microfone remoto via iPhone/Android)
    https_enabled: bool = False
    ssl_cert: str = str(DATA_DIR / "ssl" / "cert.pem")
    ssl_key: str = str(DATA_DIR / "ssl" / "key.pem")


@dataclass
class AppConfig:
    """Configuração principal."""

    agent: AgentConfig = field(default_factory=AgentConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    correction: CorrectionConfig = field(default_factory=CorrectionConfig)
    web: WebConfig = field(default_factory=WebConfig)


def load_config() -> AppConfig:
    """Carrega configuração, com override de variáveis de ambiente."""
    config = AppConfig()

    # Override por variáveis de ambiente
    if os.environ.get("IPAGENT_MODEL"):
        config.agent.model_name = os.environ["IPAGENT_MODEL"]

    if os.environ.get("IPAGENT_GPU_LAYERS"):
        config.agent.n_gpu_layers = int(os.environ["IPAGENT_GPU_LAYERS"])

    if os.environ.get("IPAGENT_PORT"):
        config.web.port = int(os.environ["IPAGENT_PORT"])

    if os.environ.get("IPAGENT_DB_PATH"):
        config.memory.db_path = os.environ["IPAGENT_DB_PATH"]

    if os.environ.get("IPAGENT_CORRECTION_ENABLED"):
        config.correction.enabled = os.environ["IPAGENT_CORRECTION_ENABLED"].lower() == "true"

    if os.environ.get("IPAGENT_HTTPS"):
        config.web.https_enabled = os.environ["IPAGENT_HTTPS"].lower() == "true"

    # Criar diretórios necessários
    SSL_DIR = DATA_DIR / "ssl"
    for dir_path in [DATA_DIR, MODELS_DIR, CONSULTATIONS_DIR, KNOWLEDGE_DIR, TRAINING_DIR, SSL_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

    return config
