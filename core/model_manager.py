"""
Gerenciador de modelos GGUF para o IPagent.
Baixa automaticamente o modelo na primeira execução.
Suporta CPU e GPU (CUDA/Metal).
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Modelos disponíveis para o IPagent
AVAILABLE_MODELS = {
    "qwen2.5-3b": {
        "repo_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_gb": 1.9,
        "description": "Qwen 2.5 3B — Rápido, bom para máquinas modestas",
        "context_length": 8192,
    },
    "qwen2.5-7b": {
        "repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "size_gb": 4.7,
        "description": "Qwen 2.5 7B — Melhor qualidade, precisa de mais memória",
        "context_length": 16384,
    },
    "llama3.2-3b": {
        "repo_id": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_gb": 2.0,
        "description": "Llama 3.2 3B — Meta AI, boa qualidade geral",
        "context_length": 8192,
    },
}

DEFAULT_MODEL = "qwen2.5-3b"


class ModelManager:
    """Gerencia download e carregamento de modelos GGUF."""

    def __init__(self, models_dir: str, model_name: str = None):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name or DEFAULT_MODEL
        self._llm = None

    def get_model_info(self) -> dict:
        """Retorna informações do modelo selecionado."""
        if self.model_name in AVAILABLE_MODELS:
            return AVAILABLE_MODELS[self.model_name]
        
        # Se for um caminho direto para .gguf
        if self.model_name.endswith(".gguf"):
            return {
                "filename": self.model_name,
                "size_gb": 0,
                "description": "Modelo customizado",
                "context_length": 8192,
            }
        
        logger.warning(f"Modelo '{self.model_name}' não encontrado. Usando {DEFAULT_MODEL}")
        self.model_name = DEFAULT_MODEL
        return AVAILABLE_MODELS[DEFAULT_MODEL]

    def get_model_path(self) -> Path:
        """Retorna o caminho do arquivo .gguf do modelo."""
        info = self.get_model_info()
        return self.models_dir / info["filename"]

    def is_downloaded(self) -> bool:
        """Verifica se o modelo já está baixado."""
        return self.get_model_path().exists()

    def download_model(self) -> Path:
        """
        Baixa o modelo do HuggingFace se não existir.
        Mostra progresso bonito no terminal.
        """
        model_path = self.get_model_path()

        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Modelo encontrado: {model_path.name} ({size_mb:.0f} MB)")
            return model_path

        info = self.get_model_info()

        if "repo_id" not in info:
            raise FileNotFoundError(
                f"Modelo '{self.model_name}' não encontrado em {self.models_dir}. "
                f"Coloque o arquivo .gguf manualmente na pasta."
            )

        try:
            from rich.console import Console
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn
            console = Console()

            console.print(f"\n[bold cyan]🧠 Baixando modelo de IA: {info['description']}[/bold cyan]")
            console.print(f"   Tamanho: ~{info['size_gb']} GB")
            console.print(f"   Fonte: HuggingFace ({info['repo_id']})")
            console.print(f"   Destino: {model_path}")
            console.print(f"   [dim]Isso acontece apenas na primeira execução![/dim]\n")

        except ImportError:
            logger.info(f"🧠 Baixando modelo: {info['description']} (~{info['size_gb']} GB)...")
            logger.info(f"   Isso acontece apenas na primeira execução!")

        try:
            from huggingface_hub import hf_hub_download

            downloaded_path = hf_hub_download(
                repo_id=info["repo_id"],
                filename=info["filename"],
                local_dir=str(self.models_dir),
                local_dir_use_symlinks=False,
            )

            logger.info(f"✅ Download concluído: {model_path.name}")
            return Path(downloaded_path)

        except Exception as e:
            logger.error(f"❌ Erro ao baixar modelo: {e}")
            logger.error(
                f"Baixe manualmente de:\n"
                f"  https://huggingface.co/{info['repo_id']}\n"
                f"E coloque o arquivo em: {self.models_dir}"
            )
            raise

    def load(self, n_gpu_layers: int = -1, n_ctx: int = None) -> "Llama":
        """
        Carrega o modelo na memória (RAM ou GPU).
        
        Args:
            n_gpu_layers: -1 = toda GPU, 0 = só CPU
            n_ctx: Tamanho do contexto (None = usa padrão do modelo)
        
        Returns:
            Instância do Llama pronta para chat
        """
        if self._llm is not None:
            return self._llm

        model_path = self.download_model()
        info = self.get_model_info()
        
        if n_ctx is None:
            n_ctx = info.get("context_length", 8192)

        logger.info(f"⏳ Carregando modelo: {model_path.name}...")
        logger.info(f"   GPU layers: {'Auto (toda GPU)' if n_gpu_layers == -1 else f'{n_gpu_layers} camadas'}")
        logger.info(f"   Contexto: {n_ctx} tokens")

        try:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
                chat_format="chatml",  # Formato compatível com Qwen/Llama
            )

            logger.info(f"✅ Modelo carregado com sucesso!")
            return self._llm

        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            
            if n_gpu_layers != 0:
                logger.info("🔄 Tentando sem GPU (modo CPU)...")
                try:
                    self._llm = Llama(
                        model_path=str(model_path),
                        n_ctx=min(n_ctx, 4096),  # Contexto menor na CPU
                        n_gpu_layers=0,
                        verbose=False,
                        chat_format="chatml",
                    )
                    logger.info("✅ Modelo carregado na CPU (mais lento, mas funciona!)")
                    return self._llm
                except Exception as e2:
                    logger.error(f"❌ Falha total: {e2}")
                    raise

            raise

    def unload(self):
        """Descarrega o modelo da memória."""
        if self._llm is not None:
            del self._llm
            self._llm = None
            logger.info("🗑️ Modelo descarregado da memória")

    @property
    def is_loaded(self) -> bool:
        return self._llm is not None

    def list_available_models(self) -> list:
        """Lista todos os modelos disponíveis."""
        models = []
        for name, info in AVAILABLE_MODELS.items():
            path = self.models_dir / info["filename"]
            models.append({
                "name": name,
                "description": info["description"],
                "size_gb": info["size_gb"],
                "downloaded": path.exists(),
                "active": name == self.model_name,
            })
        return models
