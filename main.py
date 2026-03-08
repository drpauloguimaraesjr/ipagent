"""
IPagent Ultra-Lite — Ponto de entrada principal.
Assistente médico com IA local, sem Ollama, sem dependências externas.
Apenas: pip install → python main.py
"""

import logging
import sys

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


def main():
    logger.info("🚀 Iniciando IPagent Ultra-Lite...")
    logger.info("   Sem Ollama. IA rodando direto no Python.")
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
    logger.info(f"  🧠 Modelo: {config.agent.model_name}")
    logger.info(f"  🔍 Correção médica: {'Ativada' if config.correction.enabled else 'Desativada'}")
    logger.info(f"  💾 Sem Ollama — IA 100% embutida no Python")
    logger.info("=" * 55)
    logger.info("")

    app.run(host=host, port=port, debug=config.web.debug)


if __name__ == "__main__":
    main()
