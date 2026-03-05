"""
Captura de áudio em tempo real do microfone.
Alimenta chunks de áudio para o transcritor.
"""

import logging
import threading
import queue
import time
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger(__name__)


class AudioCapture:
    """
    Captura áudio do microfone em tempo real.
    Gerencia um buffer circular e envia chunks para transcrição.
    """

    def __init__(self, config):
        """
        Inicializa a captura de áudio.
        
        Args:
            config: AudioConfig com configurações de áudio.
        """
        self.config = config
        self._stream = None
        self._is_capturing = False
        self._audio_queue = queue.Queue()
        self._buffer = np.array([], dtype=np.float32)
        self._lock = threading.Lock()
        self._on_chunk_callback: Optional[Callable] = None

    def list_devices(self) -> list:
        """Lista dispositivos de áudio disponíveis."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = []
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate'],
                    })
            return input_devices
        except Exception as e:
            logger.error(f"Erro ao listar dispositivos: {e}")
            return []

    def on_chunk_ready(self, callback: Callable[[np.ndarray], None]):
        """Registra callback para quando um chunk de áudio está pronto."""
        self._on_chunk_callback = callback

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback chamado pelo sounddevice quando novos dados de áudio chegam."""
        if status:
            logger.warning(f"Status do áudio: {status}")

        # Converter para float32 mono
        audio_data = indata[:, 0].copy().astype(np.float32)
        self._audio_queue.put(audio_data)

    def _processing_thread(self, chunk_duration: float):
        """Thread que processa e agrupa chunks de áudio."""
        samples_per_chunk = int(self.config.sample_rate * chunk_duration)

        while self._is_capturing:
            try:
                # Coletar dados da fila
                try:
                    data = self._audio_queue.get(timeout=0.5)
                    with self._lock:
                        self._buffer = np.concatenate([self._buffer, data])
                except queue.Empty:
                    continue

                # Quando tiver dados suficientes, enviar chunk
                with self._lock:
                    if len(self._buffer) >= samples_per_chunk:
                        chunk = self._buffer[:samples_per_chunk]
                        self._buffer = self._buffer[samples_per_chunk:]

                        if self._on_chunk_callback:
                            try:
                                self._on_chunk_callback(chunk)
                            except Exception as e:
                                logger.error(f"Erro no callback de chunk: {e}")

            except Exception as e:
                logger.error(f"Erro no thread de processamento: {e}")

    def start(self, chunk_duration: float = 2.0):
        """
        Inicia a captura de áudio do microfone.
        
        Args:
            chunk_duration: Duração de cada chunk em segundos.
        """
        try:
            import sounddevice as sd

            self._is_capturing = True
            self._buffer = np.array([], dtype=np.float32)

            # Iniciar stream de áudio
            device = self.config.device_index
            
            logger.info(f"🎤 Iniciando captura de áudio (device={device}, "
                       f"rate={self.config.sample_rate}Hz, "
                       f"chunk={chunk_duration}s)")

            self._stream = sd.InputStream(
                device=device,
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                blocksize=self.config.block_size,
                dtype='float32',
                callback=self._audio_callback,
            )
            self._stream.start()

            # Iniciar thread de processamento
            self._process_thread = threading.Thread(
                target=self._processing_thread,
                args=(chunk_duration,),
                daemon=True,
            )
            self._process_thread.start()

            logger.info("✅ Captura de áudio iniciada!")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar captura: {e}")
            self._is_capturing = False
            return False

    def stop(self):
        """Para a captura de áudio."""
        self._is_capturing = False
        
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Erro ao parar stream: {e}")
            self._stream = None

        # Limpar fila
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        self._buffer = np.array([], dtype=np.float32)
        logger.info("⏹️ Captura de áudio parada")

    @property
    def is_capturing(self) -> bool:
        return self._is_capturing

    def get_audio_level(self) -> float:
        """Retorna o nível de áudio atual (0.0 a 1.0) para visualização."""
        with self._lock:
            if len(self._buffer) > 0:
                rms = np.sqrt(np.mean(self._buffer[-1024:] ** 2))
                return min(1.0, rms * 10)  # Amplificar para visualização
        return 0.0
