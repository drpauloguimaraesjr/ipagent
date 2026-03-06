import logging
import sys
from pathlib import Path

from config import load_config
from core.transcriber import RealtimeTranscriber
from core.agent import MedicalAgent
from core.memory import KnowledgeMemory
from training.data_collector import DataCollector
from web.app import create_app

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("IPagent")

def main():
    logger.info("🚀 Iniciando IPagent...")
    
    # 1. Carregar configurações
    config = load_config()
    
    # 2. Inicializar componentes
    logger.info("📦 Inicializando componentes base...")
    
    memory = KnowledgeMemory(config.memory)
    memory.initialize()
    
    agent = MedicalAgent(config.agent, memory=memory)
    agent.initialize()
    
    # transcriber = RealtimeTranscriber(config.transcriber)
    # transcriber.initialize()
    transcriber = None
    
    data_collector = DataCollector(config.training)
    
    # NOTA: Removido AudioCapture local (sounddevice)
    # A captura de áudio agora será feita pelo Frontend (Navegador)
    # permitindo que o sistema rode em uma VPS sem problemas!
    
    # 3. Criar aplicação Web
    logger.info("🌐 Configurando servidor web...")
    app, socketio = create_app(
        config=config.web,
        transcriber=transcriber,
        agent=agent,
        audio=None, # Áudio agora vem do frontend
        memory=memory,
        data_collector=data_collector
    )
    
    # 4. Iniciar servidor
    host = config.web.host
    port = config.web.port
    
    # Nota de interface
    logger.info("="*50)
    logger.info(f"✨ IPagent PRONTO!")
    logger.info(f"🌍 Acesse no navegador: http://localhost:{port}")
    logger.info("="*50)
    
    socketio.run(app, host=host, port=port, debug=config.web.debug, use_reloader=False)

if __name__ == "__main__":
    main()
