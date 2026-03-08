"""
Servidor web Flask do IPagent Lite.
Versão leve: Flask puro (sem gevent, sem socketio pesado).
Usa fetch API + Server-Sent Events para comunicação em tempo real.
"""

import logging
import json
import time
import secrets
import os
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, Response, stream_with_context

logger = logging.getLogger(__name__)


def create_app(config, agent=None, memory=None, data_collector=None):
    """
    Cria a aplicação Flask com todas as rotas.
    
    Args:
        config: WebConfig
        agent: MedicalAgent instance
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

    # Estado da sessão
    session_state = {
        "is_recording": False,
        "current_transcript": "",
        "consultation_id": None,
    }

    # ==========================================
    # API Keys Management
    # ==========================================

    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    API_KEYS_FILE = DATA_DIR / "api_keys.json"

    def load_keys():
        if not API_KEYS_FILE.exists():
            return []
        try:
            with open(API_KEYS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def save_keys(keys_list):
        with open(API_KEYS_FILE, "w") as f:
            json.dump(keys_list, f, indent=4)

    def validate_api_key(f):
        """Decorador para proteger rotas com API key."""
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.headers.get("Authorization")
            if auth and auth.startswith("Bearer "):
                token = auth.split(" ")[1]
                keys = load_keys()
                is_valid = any(k["key"] == token and k.get("active", True) for k in keys)
                if not is_valid:
                    return jsonify({"error": "Chave de API inválida ou desativada."}), 403
            return f(*args, **kwargs)
        return decorated

    # ==========================================
    # Rotas de Página
    # ==========================================

    @app.route('/')
    def index():
        """Página principal."""
        return render_template('index.html')

    @app.route('/admin')
    def admin_dashboard():
        """Painel de Controle."""
        return render_template('admin.html')

    # ==========================================
    # API: Status
    # ==========================================

    @app.route('/api/status')
    def api_status():
        """Status dos componentes do sistema."""
        status = {
            "version": "ultra-lite",
            "engine": "llama-cpp-python (sem Ollama)",
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
            "correction": {
                "enabled": True,
                "engine": "llama-cpp-python + Quick Dictionary"
            }
        }
        return jsonify(status)

    # ==========================================
    # API: Transcrição + Correção Médica
    # ==========================================

    @app.route('/api/transcription/update', methods=['POST'])
    def api_transcription_update():
        """
        Recebe texto transcrito pelo navegador e acumula.
        O frontend envia trechos conforme o Speech Recognition retorna.
        """
        data = request.json or {}
        text = data.get('text', '')
        
        if text.strip():
            session_state["current_transcript"] += " " + text
            session_state["is_recording"] = True
            logger.info(f"📝 Recebido: {text[:50]}...")
        
        return jsonify({"success": True, "total_length": len(session_state["current_transcript"])})

    @app.route('/api/transcription/correct', methods=['POST'])
    @validate_api_key
    def api_correct_transcription():
        """
        🧠 CAMADA DE CORREÇÃO MÉDICA
        Recebe texto bruto do Speech Recognition e retorna corrigido.
        Usa quick-fix + LLM para máxima precisão médica.
        """
        if not agent:
            return jsonify({"error": "Agente não disponível"}), 503

        data = request.json or {}
        raw_text = data.get('text', '')

        if not raw_text.strip():
            return jsonify({"error": "Texto vazio"}), 400

        result = agent.correct_transcription(raw_text)

        # Se houve correção, registrar para futuro fine-tuning
        if data_collector and result["original"] != result["corrected"]:
            data_collector.add_transcription_correction(
                original_transcription=result["original"],
                corrected_transcription=result["corrected"],
                quality_score=0.8,  # Auto-correção tem score padrão
            )

        return jsonify(result)

    @app.route('/api/transcription/start', methods=['POST'])
    def api_start_transcription():
        """Inicia nova sessão de transcrição."""
        session_state["is_recording"] = True
        session_state["current_transcript"] = ""
        session_state["consultation_id"] = f"consult_{int(time.time())}"
        return jsonify({"success": True, "consultation_id": session_state["consultation_id"]})

    @app.route('/api/transcription/stop', methods=['POST'])
    def api_stop_transcription():
        """Para a sessão de transcrição."""
        session_state["is_recording"] = False
        return jsonify({
            "success": True,
            "transcript": session_state["current_transcript"],
            "length": len(session_state["current_transcript"])
        })

    # ==========================================
    # API: Chat com Agente
    # ==========================================

    @app.route('/api/chat', methods=['POST'])
    @validate_api_key
    def api_chat():
        """Chat com o agente médico."""
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

    @app.route('/api/chat/stream', methods=['POST'])
    @validate_api_key
    def api_chat_stream():
        """Chat com streaming via Server-Sent Events."""
        if not agent:
            return jsonify({"error": "Agente não disponível"}), 503

        data = request.json
        message = data.get('message', '')
        use_context = data.get('use_context', True)
        context = session_state["current_transcript"] if use_context else None

        def generate():
            for token in agent.chat_stream(message, context=context):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )

    # ==========================================
    # API: Análise e SOAP
    # ==========================================

    @app.route('/api/analyze', methods=['POST'])
    @validate_api_key
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
    @validate_api_key
    def api_soap():
        """Gera nota SOAP da transcrição atual."""
        if not agent:
            return jsonify({"error": "Agente não disponível"}), 503

        transcript = session_state["current_transcript"]
        if not transcript:
            return jsonify({"error": "Nenhuma transcrição disponível"}), 400

        soap = agent.generate_soap_note(transcript)
        return jsonify({"soap_note": soap})

    # ==========================================
    # API: Base de Conhecimento
    # ==========================================

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

    @app.route('/api/upload-pdf', methods=['POST'])
    def api_upload_pdf():
        """Upload e indexação de PDF científico."""
        if not memory:
            return jsonify({"error": "Memória não disponível"}), 503

        if 'file' not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400

        file = request.files['file']
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Apenas arquivos PDF são aceitos"}), 400

        # Salvar temporariamente
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = file.filename.replace(" ", "_")
        file_path = upload_dir / safe_name
        file.save(str(file_path))

        # Indexar
        success = memory.add_scientific_pdf(str(file_path))

        if success:
            return jsonify({"message": f"Artigo '{file.filename}' indexado com sucesso!"})
        else:
            return jsonify({"error": "Falha ao processar o PDF"}), 500

    # ==========================================
    # API: Feedback para Fine-tuning
    # ==========================================

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
    # API: Admin - Chaves de API
    # ==========================================

    @app.route('/api/admin/keys', methods=['GET'])
    def get_api_keys():
        return jsonify({"keys": load_keys()})

    @app.route('/api/admin/generate', methods=['POST'])
    def create_api_key():
        data = request.json or {}
        name = data.get('name', 'Sistema Externo')

        new_key = f"sk-IPagent-{secrets.token_hex(16)}"
        key_record = {
            "name": name,
            "key": new_key,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "active": True
        }

        keys = load_keys()
        keys.append(key_record)
        save_keys(keys)

        return jsonify({"success": True, "api_key": new_key})

    @app.route('/api/admin/toggle', methods=['POST'])
    def toggle_api_key():
        data = request.json or {}
        key_to_toggle = data.get('key')
        activate = data.get('active', True)

        keys = load_keys()
        for k in keys:
            if k["key"] == key_to_toggle:
                k["active"] = activate
                break
        save_keys(keys)
        return jsonify({"success": True})

    @app.route('/api/admin/delete', methods=['POST'])
    def delete_api_key():
        data = request.json or {}
        key_to_delete = data.get('key')

        keys = load_keys()
        keys = [k for k in keys if k["key"] != key_to_delete]
        save_keys(keys)
        return jsonify({"success": True})

    # Rota legada para compatibilidade
    @app.route('/api/generate-key', methods=['POST'])
    def generate_key_legacy():
        return create_api_key()

    # ==========================================
    # Base de Conhecimento
    # ==========================================

    @app.route('/knowledge')
    def knowledge_page():
        """Página de Base de Conhecimento."""
        return render_template('knowledge.html')

    @app.route('/api/knowledge/list')
    def list_knowledge():
        """Lista consultas e artigos da base de conhecimento."""
        consultations = []
        articles = []

        if memory and memory.is_initialized:
            try:
                import sqlite3
                conn = sqlite3.connect(memory.db_path)
                cursor = conn.cursor()

                # Consultas
                cursor.execute(
                    "SELECT content, category, source FROM documents WHERE category = 'consultation' ORDER BY rowid DESC LIMIT 50"
                )
                for row in cursor.fetchall():
                    content_text = row[0]
                    consultations.append({
                        "content": content_text,
                        "diagnosis": content_text[:60] + "..." if len(content_text) > 60 else content_text,
                        "date": row[2] if row[2] else "",
                    })

                # Artigos/Literatura
                cursor.execute(
                    "SELECT content, category, source FROM documents WHERE category != 'consultation' ORDER BY rowid DESC LIMIT 50"
                )
                for row in cursor.fetchall():
                    content_text = row[0]
                    articles.append({
                        "content": content_text,
                        "filename": row[2] if row[2] else "Artigo",
                        "category": row[1],
                    })

                conn.close()
            except Exception as e:
                logger.error(f"Erro ao listar knowledge: {e}")

        return jsonify({
            "consultations": consultations,
            "articles": articles
        })

    return app
