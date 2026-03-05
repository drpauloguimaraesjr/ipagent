"""
Servidor web Flask com WebSocket para interface do IPagent.
Fornece UI para transcrição em tempo real e chat com o agente.
"""

import logging
import json
import time
import threading
import os
from pathlib import Path
import numpy as np
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

logger = logging.getLogger(__name__)


def create_app(config, transcriber=None, agent=None, audio=None, memory=None, data_collector=None):
    """
    Cria a aplicação Flask com todas as rotas e WebSocket.
    
    Args:
        config: WebConfig
        transcriber: RealtimeTranscriber instance
        agent: MedicalAgent instance
        audio: AudioCapture instance
        memory: KnowledgeMemory instance
        data_collector: DataCollector instance
    """
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    app.config['SECRET_KEY'] = config.secret_key

    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

    # Estado da sessão
    session_state = {
        "is_recording": False,
        "current_transcript": "",
        "consultation_id": None,
    }

    # ==========================================
    # Rotas HTTP
    # ==========================================

    @app.route('/')
    def index():
        """Página principal."""
        return render_template('index.html')

    @app.route('/api/status')
    def api_status():
        """Status dos componentes do sistema."""
        status = {
            "transcriber": {
                "initialized": transcriber.is_initialized if transcriber else False,
                "running": transcriber.is_running if transcriber else False,
            },
            "agent": {
                "available": agent.is_available if agent else False,
            },
            "memory": {
                "initialized": memory.is_initialized if memory else False,
                "stats": memory.get_stats() if memory and memory.is_initialized else {},
            },
            "training": {
                "examples": data_collector.example_count if data_collector else 0,
                "ready": data_collector.is_ready_for_training if data_collector else False,
                "stats": data_collector.get_stats() if data_collector else {},
            },
            "audio": {
                "capturing": audio.is_capturing if audio else False,
            },
        }
        return jsonify(status)

    @app.route('/api/devices')
    def api_devices():
        """Lista dispositivos de áudio disponíveis."""
        if audio:
            devices = audio.list_devices()
            return jsonify({"devices": devices})
        return jsonify({"devices": [], "error": "Audio não inicializado"})

    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        """Endpoint de chat com o agente."""
        if not agent:
            return jsonify({"error": "Agente não disponível"}), 503

        data = request.json
        message = data.get('message', '')
        use_context = data.get('use_context', True)

        context = session_state["current_transcript"] if use_context else None
        response = agent.chat(message, context=context)

        return jsonify({
            "response": response,
            "timestamp": time.time(),
        })

    @app.route('/api/analyze', methods=['POST'])
    def api_analyze():
        """Analisa a transcrição atual."""
        if not agent:
            return jsonify({"error": "Agente não disponível"}), 503

        transcript = session_state["current_transcript"]
        if not transcript:
            return jsonify({"error": "Nenhuma transcrição disponível"}), 400

        analysis = agent.analyze_transcription(transcript)
        return jsonify({"analysis": analysis})

    @app.route('/api/soap', methods=['POST'])
    def api_soap():
        """Gera nota SOAP da transcrição atual."""
        if not agent:
            return jsonify({"error": "Agente não disponível"}), 503

        transcript = session_state["current_transcript"]
        if not transcript:
            return jsonify({"error": "Nenhuma transcrição disponível"}), 400

        soap = agent.generate_soap_note(transcript)
        return jsonify({"soap_note": soap})

    @app.route('/api/save-consultation', methods=['POST'])
    def api_save_consultation():
        """Salva a consulta atual na base de conhecimento."""
        if not memory:
            return jsonify({"error": "Memória não disponível"}), 503

        data = request.json
        transcript = data.get('transcript', session_state["current_transcript"])
        patient_id = data.get('patient_id')
        diagnosis = data.get('diagnosis')
        notes = data.get('notes')

        success = memory.add_consultation(
            transcription=transcript,
            patient_id=patient_id,
            diagnosis=diagnosis,
            notes=notes,
        )

        return jsonify({"success": success})

    @app.route('/api/feedback', methods=['POST'])
    def api_feedback():
        """Recebe feedback do médico para treinamento."""
        if not data_collector:
            return jsonify({"error": "Coletor de dados não disponível"}), 503

        data = request.json
        feedback_type = data.get('type')

        if feedback_type == 'transcription_correction':
            data_collector.add_transcription_correction(
                original_transcription=data.get('original', ''),
                corrected_transcription=data.get('corrected', ''),
                quality_score=data.get('quality', 1.0),
            )
        elif feedback_type == 'soap_correction':
            data_collector.add_soap_example(
                transcription=data.get('transcription', ''),
                soap_note=data.get('soap_note', ''),
                quality_score=data.get('quality', 1.0),
            )
        elif feedback_type == 'response_correction':
            data_collector.add_feedback(
                agent_response=data.get('original_response', ''),
                corrected_response=data.get('corrected_response', ''),
                original_query=data.get('query', ''),
                quality_score=data.get('quality', 1.0),
            )
        else:
            return jsonify({"error": f"Tipo de feedback inválido: {feedback_type}"}), 400

        return jsonify({
            "success": True,
            "total_examples": data_collector.example_count,
        })

    @app.route('/api/training/stats')
    def api_training_stats():
        """Estatísticas do dataset de treinamento."""
        if data_collector:
            return jsonify(data_collector.get_stats())
        return jsonify({"error": "Coletor não disponível"}), 503

    # ==========================================
    # WebSocket Events
    # ==========================================

    @socketio.on('connect')
    def handle_connect():
        """Cliente conectou."""
        logger.info("🔌 Cliente WebSocket conectado")
        emit('status', {'connected': True})

    @socketio.on('start_transcribing_from_web')
    def handle_start_web_transcription(data):
        """Inicia a transcrição recebendo áudio do navegador (VPS compatible)."""
        if not transcriber:
            emit('error', {'message': 'Transcritor não disponível'})
            return

        session_state["is_recording"] = True
        session_state["current_transcript"] = ""
        transcriber.start_session()
        
        def on_transcription(segment):
            session_state["current_transcript"] += " " + segment.text
            socketio.emit('transcription_update', {
                'text': segment.text
            })

        transcriber.on_transcription(on_transcription)
        logger.info("🎙️ Recebendo streaming de áudio do navegador...")

    @socketio.on('audio_chunk')
    def handle_audio_chunk(data):
        """Recebe pacotes PCM Int16 do navegador e envia pro Whisper."""
        if not session_state["is_recording"] or not transcriber:
            return
            
        try:
            # Converter Int16Array Buffer to np.float32 array que Whispers espera
            audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Aqui deveriamos acumular chunks até ter 2 segundos e depois enviar.
            # Para simplificar na alteração do código:
            # (Numa versao de produçao real voce gerencia o buffer aqui)
            transcriber.transcribe_chunk(audio_array)
            
        except Exception as e:
            logger.error(f"Erro processando chunk de web: {e}")

    @socketio.on('stop_transcribing_from_web')
    def handle_stop_web_transcription():
        """Para a transcrição do navegador."""
        session_state["is_recording"] = False
        if transcriber:
            transcriber.stop_session()
        logger.info("⏹️ Streaming de áudio do navegador parado")

    @socketio.on('chat_message')
    def handle_chat_message(data):
        """Mensagem de chat via WebSocket (com streaming)."""
        if not agent:
            emit('error', {'message': 'Agente não disponível'})
            return

        message = data.get('message', '')
        use_context = data.get('use_context', True)
        context = session_state["current_transcript"] if use_context else None

        # Streaming response
        emit('chat_start', {})
        for token in agent.chat_stream(message, context=context):
            emit('chat_token', {'token': token})
        emit('chat_end', {})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Cliente desconectou."""
        logger.info("🔌 Cliente WebSocket desconectado")
        if session_state["is_recording"]:
            handle_stop_web_transcription()

    return app, socketio
