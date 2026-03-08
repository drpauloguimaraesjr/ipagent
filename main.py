"""
IPagent Ultra-Lite — Ponto de entrada principal.
Assistente médico com IA local, sem Ollama, sem dependências externas.
Apenas: pip install → python main.py

💰 Custo de operação: R$ 0,00 — IA 100% local e open source.
"""

import logging
import os
import sys
import threading
import webbrowser

from config import load_config
from core.model_manager import ModelManager
from core.agent import MedicalAgent
from core.memory import KnowledgeMemory
from training.data_collector import DataCollector
from web.app import create_app

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("IPagent")


def open_browser(port: int):
    """
    Abre o navegador automaticamente após o servidor iniciar.
    Usa um timer para dar tempo do Flask ficar pronto.
    """
    url = f"http://localhost:{port}"
    try:
        webbrowser.open(url)
        logger.info(f"🌐 Navegador aberto em: {url}")
    except Exception:
        logger.info(f"🌐 Abra manualmente no navegador: {url}")


def main():
    logger.info("🚀 Iniciando IPagent Ultra-Lite...")
    logger.info("   Sem Ollama. IA rodando direto no Python.")
    logger.info("   💰 Custo: R$ 0,00 — IA 100% local e open source.")
    logger.info("")

    # 1. Carregar configurações
    config = load_config()

    # 2. Gerenciador de modelos (download automático na 1ª vez)
    logger.info("🧠 Preparando modelo de IA...")
    model_manager = ModelManager(
        models_dir=config.agent.models_dir,
        model_name=config.agent.model_name
    )

    # Mostra modelos disponíveis
    for m in model_manager.list_available_models():
        status = "✅ baixado" if m["downloaded"] else f"⏳ {m['size_gb']} GB para baixar"
        active = " ← ATIVO" if m["active"] else ""
        logger.info(f"   {m['name']}: {m['description']} [{status}]{active}")

    # 3. Base de conhecimento (SQLite FTS5)
    logger.info("📚 Inicializando base de conhecimento...")
    memory = KnowledgeMemory(config.memory)
    memory.initialize()

    # 4. Agente LLM + Correção Médica
    logger.info("🤖 Inicializando agente médico...")
    agent = MedicalAgent(
        config=config.agent,
        model_manager=model_manager,
        memory=memory,
        correction_config=config.correction
    )
    agent.initialize()

    # 5. Coletor de dados para futuro fine-tuning
    data_collector = DataCollector(config.training)

    # 6. Criar aplicação Web
    logger.info("🌐 Configurando servidor web...")
    app = create_app(
        config=config.web,
        agent=agent,
        memory=memory,
        data_collector=data_collector
    )

    # 7. Iniciar servidor
    host = config.web.host
    port = config.web.port

    logger.info("")
    logger.info("=" * 55)
    logger.info("  ✨ IPagent Ultra-Lite PRONTO!")
    logger.info(f"  🌍 Acesse: http://localhost:{port}")
    logger.info(f"  🔧 Admin:  http://localhost:{port}/admin")
    logger.info(f"  📚 Base:   http://localhost:{port}/knowledge")
    logger.info(f"  🧠 Modelo: {config.agent.model_name}")
    logger.info(f"  🔍 Correção médica: {'Ativada' if config.correction.enabled else 'Desativada'}")
    logger.info(f"  💰 Custo: R$ 0,00 — IA 100% local")
    logger.info("=" * 55)
    logger.info("")
    logger.info("  Para parar: Ctrl+C")
    logger.info("  Para reabrir: ./run.sh (Linux/Mac) ou run.bat (Windows)")
    logger.info("")

    # 8. Abrir navegador automaticamente (se não for reloader do Flask)
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        # Abre o navegador após 1.5s (tempo do Flask iniciar)
        timer = threading.Timer(1.5, open_browser, args=[port])
        timer.daemon = True
        timer.start()

    app.run(host=host, port=port, debug=config.web.debug)


if __name__ == "__main__":
    main()
