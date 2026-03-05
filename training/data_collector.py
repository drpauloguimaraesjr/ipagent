"""
Coletor de dados para fine-tuning progressivo.
Formata transcrições e feedback em pares de treinamento.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """Um exemplo de treinamento para fine-tuning."""
    instruction: str
    input_text: str
    output_text: str
    category: str  # "transcription_correction", "soap_note", "diagnosis", etc.
    quality_score: float = 1.0  # 0.0 a 1.0 (feedback do médico)
    created_at: float = 0.0
    metadata: Dict = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.metadata is None:
            self.metadata = {}


class DataCollector:
    """
    Coleta e formata dados para fine-tuning do modelo.
    Converte experiências de consulta em exemplos de treinamento.
    """

    def __init__(self, config):
        """
        Args:
            config: TrainingConfig com configurações.
        """
        self.config = config
        self.datasets_dir = Path(config.datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self._examples: List[TrainingExample] = []
        self._load_existing()

    def _load_existing(self):
        """Carrega exemplos existentes do disco."""
        dataset_file = self.datasets_dir / "training_data.jsonl"
        if dataset_file.exists():
            try:
                with open(dataset_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        self._examples.append(TrainingExample(**data))
                logger.info(f"📂 {len(self._examples)} exemplos de treinamento carregados")
            except Exception as e:
                logger.error(f"Erro ao carregar dados: {e}")

    def _save(self):
        """Salva todos os exemplos no disco."""
        dataset_file = self.datasets_dir / "training_data.jsonl"
        try:
            with open(dataset_file, 'w', encoding='utf-8') as f:
                for example in self._examples:
                    f.write(json.dumps(asdict(example), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro ao salvar dados: {e}")

    def add_transcription_correction(
        self,
        original_transcription: str,
        corrected_transcription: str,
        quality_score: float = 1.0,
    ):
        """
        Adiciona correção de transcrição como exemplo de treinamento.
        Quando o médico corrige a transcrição, aprendemos com isso.
        
        Args:
            original_transcription: Texto original transcrito.
            corrected_transcription: Texto corrigido pelo médico.
            quality_score: Qualidade da correção (0.0 a 1.0).
        """
        example = TrainingExample(
            instruction="Corrija e melhore a seguinte transcrição médica, "
                       "ajustando termos técnicos e formatação:",
            input_text=original_transcription,
            output_text=corrected_transcription,
            category="transcription_correction",
            quality_score=quality_score,
        )
        self._examples.append(example)
        self._save()
        logger.info("📝 Correção de transcrição adicionada ao dataset")

    def add_soap_example(
        self,
        transcription: str,
        soap_note: str,
        quality_score: float = 1.0,
    ):
        """
        Adiciona exemplo de nota SOAP para treinamento.
        
        Args:
            transcription: Transcrição da consulta.
            soap_note: Nota SOAP gerada/corrigida pelo médico.
            quality_score: Qualidade do exemplo.
        """
        example = TrainingExample(
            instruction="Gere uma nota médica no formato SOAP "
                       "(Subjetivo, Objetivo, Avaliação, Plano) "
                       "a partir da seguinte transcrição de consulta:",
            input_text=transcription,
            output_text=soap_note,
            category="soap_note",
            quality_score=quality_score,
        )
        self._examples.append(example)
        self._save()
        logger.info("📝 Exemplo SOAP adicionado ao dataset")

    def add_qa_example(
        self,
        question: str,
        answer: str,
        context: Optional[str] = None,
        quality_score: float = 1.0,
    ):
        """
        Adiciona par pergunta-resposta médica.
        
        Args:
            question: Pergunta feita durante a consulta.
            answer: Resposta correta/ideal.
            context: Contexto adicional.
            quality_score: Qualidade do exemplo.
        """
        instruction = "Responda a seguinte pergunta médica de forma clara e profissional:"
        input_text = question
        if context:
            input_text = f"Contexto: {context}\n\nPergunta: {question}"

        example = TrainingExample(
            instruction=instruction,
            input_text=input_text,
            output_text=answer,
            category="medical_qa",
            quality_score=quality_score,
        )
        self._examples.append(example)
        self._save()
        logger.info("📝 Exemplo Q&A adicionado ao dataset")

    def add_feedback(
        self,
        agent_response: str,
        corrected_response: str,
        original_query: str,
        quality_score: float = 1.0,
    ):
        """
        Adiciona feedback sobre resposta do agente.
        Quando o médico corrige uma resposta do agente, aprendemos.
        
        Args:
            agent_response: Resposta original do agente.
            corrected_response: Resposta corrigida pelo médico.
            original_query: Pergunta/comando original.
            quality_score: Qualidade da correção.
        """
        example = TrainingExample(
            instruction=original_query,
            input_text=f"Resposta anterior (incorreta/incompleta): {agent_response}",
            output_text=corrected_response,
            category="feedback_correction",
            quality_score=quality_score,
        )
        self._examples.append(example)
        self._save()
        logger.info("📝 Feedback de correção adicionado ao dataset")

    def export_for_training(self, min_quality: float = 0.5) -> Path:
        """
        Exporta dados formatados para fine-tuning com unsloth.
        
        Args:
            min_quality: Score mínimo de qualidade para incluir.
            
        Returns:
            Caminho do arquivo exportado.
        """
        filtered = [ex for ex in self._examples if ex.quality_score >= min_quality]
        
        output_file = self.datasets_dir / "fine_tuning_data.json"
        
        # Formato Alpaca (compatível com unsloth)
        training_data = []
        for ex in filtered:
            training_data.append({
                "instruction": ex.instruction,
                "input": ex.input_text,
                "output": ex.output_text,
            })

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"📦 Dataset exportado: {len(training_data)} exemplos "
            f"(de {len(self._examples)} totais, filtro qualidade >= {min_quality})"
        )
        return output_file

    def get_stats(self) -> Dict:
        """Retorna estatísticas do dataset."""
        categories = {}
        for ex in self._examples:
            categories[ex.category] = categories.get(ex.category, 0) + 1

        return {
            "total_examples": len(self._examples),
            "categories": categories,
            "avg_quality": (
                sum(ex.quality_score for ex in self._examples) / len(self._examples)
                if self._examples else 0
            ),
            "ready_for_training": len(self._examples) >= self.config.min_training_samples,
            "min_required": self.config.min_training_samples,
        }

    @property
    def example_count(self) -> int:
        return len(self._examples)

    @property
    def is_ready_for_training(self) -> bool:
        return len(self._examples) >= self.config.min_training_samples
