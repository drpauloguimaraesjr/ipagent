"""
Pipeline de fine-tuning usando unsloth + QLoRA.
Permite treinar o modelo progressivamente com dados de consultas.

NOTA: Este módulo requer instalação separada do unsloth:
  pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
  pip install --no-deps trl peft accelerate bitsandbytes
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class FineTuner:
    """
    Pipeline de fine-tuning com unsloth + QLoRA.
    Treina o modelo localmente com eficiência de memória.
    
    Suporta tanto execução local (RTX 4060 8GB) quanto
    em VPS com GPU mais potente (A100, H100).
    """

    def __init__(self, config):
        """
        Args:
            config: TrainingConfig com configurações.
        """
        self.config = config
        self._model = None
        self._tokenizer = None
        self._is_ready = False

    def check_environment(self) -> Dict:
        """Verifica se o ambiente está pronto para fine-tuning."""
        status = {
            "unsloth_installed": False,
            "torch_available": False,
            "cuda_available": False,
            "gpu_name": "N/A",
            "gpu_memory": "N/A",
            "ready": False,
        }

        try:
            import torch
            status["torch_available"] = True
            status["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                status["gpu_name"] = torch.cuda.get_device_name(0)
                mem = torch.cuda.get_device_properties(0).total_mem
                status["gpu_memory"] = f"{mem / 1e9:.1f} GB"
        except ImportError:
            pass

        try:
            import unsloth
            status["unsloth_installed"] = True
        except ImportError:
            pass

        status["ready"] = (
            status["unsloth_installed"] 
            and status["torch_available"] 
            and status["cuda_available"]
        )

        return status

    def prepare_model(self) -> bool:
        """
        Prepara o modelo base para fine-tuning com QLoRA.
        
        Returns:
            True se o modelo foi preparado com sucesso.
        """
        try:
            from unsloth import FastLanguageModel

            logger.info(f"📥 Carregando modelo base: {self.config.base_model}")

            self._model, self._tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.config.base_model,
                max_seq_length=self.config.max_seq_length,
                dtype=None,  # Auto-detect
                load_in_4bit=True,  # QLoRA - 4bit quantization
            )

            # Configurar LoRA
            self._model = FastLanguageModel.get_peft_model(
                self._model,
                r=self.config.lora_rank,
                target_modules=[
                    "q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj",
                ],
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                bias="none",
                use_gradient_checkpointing="unsloth",  # Economiza VRAM
                random_state=42,
            )

            self._is_ready = True
            logger.info("✅ Modelo preparado para fine-tuning (QLoRA)")
            return True

        except ImportError as e:
            logger.error(
                f"❌ Dependências de fine-tuning não instaladas: {e}\n"
                "Execute:\n"
                '  pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"\n'
                "  pip install --no-deps trl peft accelerate bitsandbytes"
            )
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao preparar modelo: {e}")
            return False

    def train(self, dataset_path: str, output_name: Optional[str] = None) -> bool:
        """
        Executa o fine-tuning com os dados fornecidos.
        
        Args:
            dataset_path: Caminho para o arquivo JSON no formato Alpaca.
            output_name: Nome do modelo de saída (opcional).
            
        Returns:
            True se o treinamento foi bem sucedido.
        """
        if not self._is_ready:
            logger.error("Modelo não preparado. Chame prepare_model() primeiro.")
            return False

        try:
            from trl import SFTTrainer
            from transformers import TrainingArguments
            from datasets import load_dataset
            from unsloth import is_bfloat16_supported

            logger.info(f"📂 Carregando dataset: {dataset_path}")

            # Carregar dataset
            dataset = load_dataset("json", data_files=dataset_path, split="train")

            # Template de formatação (Alpaca)
            alpaca_template = """Abaixo está uma instrução que descreve uma tarefa, junto com uma entrada que fornece mais contexto. Escreva uma resposta que complete adequadamente o pedido.

### Instrução:
{instruction}

### Entrada:
{input}

### Resposta:
{output}"""

            def formatting_func(examples):
                texts = []
                for i in range(len(examples["instruction"])):
                    text = alpaca_template.format(
                        instruction=examples["instruction"][i],
                        input=examples["input"][i],
                        output=examples["output"][i],
                    )
                    texts.append(text + self._tokenizer.eos_token)
                return {"text": texts}

            dataset = dataset.map(formatting_func, batched=True)

            # Configurar output
            if output_name is None:
                output_name = f"ipagent_ft_{int(time.time())}"
            
            output_dir = Path(self.config.output_dir) / output_name
            output_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                f"🏋️ Iniciando treinamento:\n"
                f"  - Exemplos: {len(dataset)}\n"
                f"  - Épocas: {self.config.num_epochs}\n"
                f"  - Batch size: {self.config.batch_size}\n"
                f"  - Learning rate: {self.config.learning_rate}\n"
                f"  - LoRA rank: {self.config.lora_rank}\n"
                f"  - Output: {output_dir}"
            )

            # Configurar trainer
            trainer = SFTTrainer(
                model=self._model,
                tokenizer=self._tokenizer,
                train_dataset=dataset,
                dataset_text_field="text",
                max_seq_length=self.config.max_seq_length,
                dataset_num_proc=2,
                packing=False,
                args=TrainingArguments(
                    per_device_train_batch_size=self.config.batch_size,
                    gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                    warmup_steps=5,
                    num_train_epochs=self.config.num_epochs,
                    learning_rate=self.config.learning_rate,
                    fp16=not is_bfloat16_supported(),
                    bf16=is_bfloat16_supported(),
                    logging_steps=1,
                    optim="adamw_8bit",
                    weight_decay=0.01,
                    lr_scheduler_type="linear",
                    seed=42,
                    output_dir=str(output_dir),
                    report_to="none",
                ),
            )

            # Treinar
            train_result = trainer.train()

            logger.info(
                f"✅ Treinamento concluído!\n"
                f"  - Loss final: {train_result.training_loss:.4f}\n"
                f"  - Steps: {train_result.global_step}"
            )

            # Salvar modelo LoRA
            self._model.save_pretrained(str(output_dir / "lora_adapter"))
            self._tokenizer.save_pretrained(str(output_dir / "lora_adapter"))

            logger.info(f"💾 Adaptador LoRA salvo em: {output_dir / 'lora_adapter'}")

            # Salvar metadados
            metadata = {
                "base_model": self.config.base_model,
                "lora_rank": self.config.lora_rank,
                "training_examples": len(dataset),
                "epochs": self.config.num_epochs,
                "final_loss": train_result.training_loss,
                "timestamp": time.time(),
                "output_name": output_name,
            }
            with open(output_dir / "training_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"❌ Erro durante o treinamento: {e}")
            import traceback
            traceback.print_exc()
            return False

    def export_to_ollama(self, adapter_path: str, model_name: str = "ipagent-medical") -> bool:
        """
        Exporta o modelo fine-tuned para o Ollama (GGUF).
        
        Args:
            adapter_path: Caminho para o adaptador LoRA.
            model_name: Nome do modelo no Ollama.
            
        Returns:
            True se a exportação foi bem sucedida.
        """
        try:
            from unsloth import FastLanguageModel

            logger.info("📦 Exportando modelo para formato GGUF (Ollama)...")

            output_dir = Path(adapter_path).parent / "gguf"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Salvar em formato GGUF quantizado
            if self._model and self._tokenizer:
                self._model.save_pretrained_gguf(
                    str(output_dir),
                    self._tokenizer,
                    quantization_method="q4_k_m",  # Bom equilíbrio qualidade/tamanho
                )

                # Criar Modelfile para Ollama
                modelfile_content = f"""FROM {output_dir}/unsloth.Q4_K_M.gguf

PARAMETER temperature 0.3
PARAMETER num_ctx 8192

SYSTEM \"\"\"Você é um assistente médico inteligente chamado IPagent.
Sua função é auxiliar o profissional de saúde durante consultas médicas.
Você foi treinado especificamente com dados de consultas reais para melhorar
sua precisão com terminologia médica e padrões clínicos.
Sempre responda em português, de forma clara e profissional.\"\"\"
"""
                modelfile_path = output_dir / "Modelfile"
                with open(modelfile_path, 'w') as f:
                    f.write(modelfile_content)

                logger.info(
                    f"✅ Modelo GGUF exportado!\n"
                    f"Para instalar no Ollama, execute:\n"
                    f"  ollama create {model_name} -f {modelfile_path}"
                )
                return True
            else:
                logger.error("Modelo não carregado. Execute prepare_model() primeiro.")
                return False

        except Exception as e:
            logger.error(f"❌ Erro na exportação: {e}")
            return False

    def list_fine_tuned_models(self) -> list:
        """Lista modelos fine-tuned disponíveis."""
        output_dir = Path(self.config.output_dir)
        models = []
        
        if output_dir.exists():
            for model_dir in output_dir.iterdir():
                if model_dir.is_dir():
                    metadata_file = model_dir / "training_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        models.append({
                            "name": model_dir.name,
                            "path": str(model_dir),
                            **metadata,
                        })

        return sorted(models, key=lambda x: x.get("timestamp", 0), reverse=True)

    @property
    def is_ready(self) -> bool:
        return self._is_ready
