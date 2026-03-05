"""
Motor de transcrição em tempo real usando faster-whisper.
Converte áudio do microfone em texto com baixa latência.
"""

import logging
import threading
import time
from typing import Optional, Callable, List
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """Segmento de transcrição com metadados."""
    text: str
    start_time: float
    end_time: float
    confidence: float
    language: str = "pt"
    is_partial: bool = False


class RealtimeTranscriber:
    """
    Motor de transcrição em tempo real.
    Usa faster-whisper para converter áudio em texto com baixa latência.
    """

    def __init__(self, config):
        """
        Inicializa o transcritor.
        
        Args:
            config: TranscriberConfig com as configurações do Whisper.
        """
        self.config = config
        self.model = None
        self._is_running = False
        self._lock = threading.Lock()
        self._callbacks: List[Callable] = []
        self._transcription_history: List[TranscriptionSegment] = []
        self._session_start_time: Optional[float] = None

    def initialize(self):
        """Carrega o modelo faster-whisper. Pode demorar no primeiro uso (download)."""
        try:
            from faster_whisper import WhisperModel

            logger.info(
                f"Carregando modelo Whisper '{self.config.model_size}' "
                f"no dispositivo '{self.config.device}'..."
            )

            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )

            logger.info("✅ Modelo Whisper carregado com sucesso!")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo Whisper: {e}")
            logger.info(
                "Tentando carregar na CPU como fallback..."
            )
            try:
                from faster_whisper import WhisperModel

                self.model = WhisperModel(
                    self.config.model_size,
                    device="cpu",
                    compute_type="int8",
                )
                logger.info("✅ Modelo Whisper carregado na CPU (fallback)")
                return True
            except Exception as e2:
                logger.error(f"❌ Falha total ao carregar Whisper: {e2}")
                return False

    def on_transcription(self, callback: Callable[[TranscriptionSegment], None]):
        """Registra callback para receber transcrições."""
        self._callbacks.append(callback)

    def transcribe_chunk(self, audio_data: np.ndarray) -> Optional[TranscriptionSegment]:
        """
        Transcreve um chunk de áudio.
        
        Args:
            audio_data: Array numpy com dados de áudio (float32, 16kHz, mono).
            
        Returns:
            TranscriptionSegment com o texto transcrito, ou None se silêncio.
        """
        if self.model is None:
            logger.warning("Modelo não inicializado. Chame initialize() primeiro.")
            return None

        if audio_data is None or len(audio_data) == 0:
            return None

        # Garantir formato correto
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Normalizar se necessário
        max_val = np.max(np.abs(audio_data))
        if max_val > 1.0:
            audio_data = audio_data / max_val

        # Verificar energia do áudio (filtro básico de silêncio)
        energy = np.sqrt(np.mean(audio_data ** 2))
        if energy < 0.01:
            return None

        try:
            vad_filter = self.config.use_vad
            
            segments, info = self.model.transcribe(
                audio_data,
                language=self.config.language,
                beam_size=self.config.beam_size,
                vad_filter=vad_filter,
                vad_parameters=dict(
                    threshold=self.config.vad_threshold,
                    min_speech_duration_ms=250,
                    max_speech_duration_s=30,
                    min_silence_duration_ms=500,
                ) if vad_filter else None,
                without_timestamps=False,
            )

            full_text = ""
            seg_start = 0.0
            seg_end = 0.0
            avg_prob = 0.0
            seg_count = 0

            for segment in segments:
                text = segment.text.strip()
                if text:
                    full_text += text + " "
                    if seg_count == 0:
                        seg_start = segment.start
                    seg_end = segment.end
                    avg_prob += segment.avg_log_prob
                    seg_count += 1

            full_text = full_text.strip()

            if not full_text:
                return None

            if seg_count > 0:
                avg_prob /= seg_count

            # Converter log prob para confidence (0-1)
            confidence = min(1.0, max(0.0, 1.0 + avg_prob))

            # Calcular tempo relativo à sessão
            elapsed = 0.0
            if self._session_start_time:
                elapsed = time.time() - self._session_start_time

            result = TranscriptionSegment(
                text=full_text,
                start_time=elapsed + seg_start,
                end_time=elapsed + seg_end,
                confidence=confidence,
                language=info.language if info else "pt",
                is_partial=False,
            )

            # Armazenar no histórico
            self._transcription_history.append(result)

            # Notificar callbacks
            for callback in self._callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Erro no callback de transcrição: {e}")

            return result

        except Exception as e:
            logger.error(f"Erro na transcrição: {e}")
            return None

    def start_session(self):
        """Inicia uma nova sessão de transcrição."""
        self._session_start_time = time.time()
        self._transcription_history = []
        self._is_running = True
        logger.info("🎙️ Sessão de transcrição iniciada")

    def stop_session(self):
        """Para a sessão de transcrição."""
        self._is_running = False
        logger.info("⏹️ Sessão de transcrição parada")

    def get_full_transcript(self) -> str:
        """Retorna a transcrição completa da sessão atual."""
        return " ".join(seg.text for seg in self._transcription_history)

    def get_history(self) -> List[TranscriptionSegment]:
        """Retorna o histórico de segmentos transcritos."""
        return self._transcription_history.copy()

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_initialized(self) -> bool:
        return self.model is not None
