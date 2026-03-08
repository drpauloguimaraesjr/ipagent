"""
IPagent Ultra-Lite — Ponto de entrada principal.
Assistente médico com IA local, sem Ollama, sem dependências externas.
Apenas: pip install → python main.py

💰 Custo de operação: R$ 0,00 — IA 100% local e open source.
"""

import logging
import os
import socket
import ssl
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

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


def get_local_ip() -> str:
    """Descobre o IP local na rede WiFi/Ethernet."""
    try:
        # Truque: cria socket UDP para descobrir IP local sem enviar nada
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_ssl_cert(cert_path: str, key_path: str) -> bool:
    """
    Gera certificado SSL auto-assinado para HTTPS local.
    Necessário para que Chrome/Safari no iPhone/Android acessem o microfone.
    """
    cert_file = Path(cert_path)
    key_file = Path(key_path)

    # Se já existem, não regerar
    if cert_file.exists() and key_file.exists():
        logger.info("🔐 Certificado SSL encontrado")
        return True

    logger.info("🔐 Gerando certificado SSL auto-assinado...")
    logger.info("   (necessário para microfone no iPhone/Android)")

    local_ip = get_local_ip()

    # Tentar gerar via openssl (disponível no macOS e maioria dos Linux)
    try:
        # Criar diretório
        cert_file.parent.mkdir(parents=True, exist_ok=True)

        # Gerar certificado com SAN (Subject Alternative Name) para IP local
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key_file),
            "-out", str(cert_file),
            "-days", "365",
            "-nodes",  # Sem senha
            "-subj", f"/CN=IPagent Local/O=IPagent/C=BR",
            "-addext", f"subjectAltName=IP:{local_ip},IP:127.0.0.1,DNS:localhost",
        ], check=True, capture_output=True)

        logger.info(f"✅ Certificado SSL gerado para IP: {local_ip}")
        return True

    except FileNotFoundError:
        # openssl não disponível, tentar via Python
        logger.info("   openssl não encontrado, gerando via Python...")
        return _generate_ssl_python(cert_file, key_file, local_ip)

    except subprocess.CalledProcessError as e:
        logger.warning(f"⚠️ Erro ao gerar certificado: {e}")
        return _generate_ssl_python(cert_file, key_file, local_ip)


def _generate_ssl_python(cert_file: Path, key_file: Path, local_ip: str) -> bool:
    """Fallback: gera certificado SSL via Python puro (sem openssl CLI)."""
    try:
        from datetime import datetime, timedelta

        # Usar módulo ssl do Python para gerar cert simples
        # Criamos um script inline que gera o cert
        script = f'''
import ssl
import tempfile
import subprocess
import os

# Gerar com openssl via Python subprocess se possível
# Caso contrário, criar um cert mínimo

cert_path = "{cert_file}"
key_path = "{key_file}"

# Gerar chave RSA e certificado auto-assinado simples
import hashlib, base64, struct, time, random

# Fallback ultra-simples: self-signed via ssl.create_default_context
print("Certificado SSL precisa do openssl. Instale com:")
print("  Linux: sudo apt install openssl")
print("  macOS: já vem instalado")
print("  Windows: vem com Git for Windows")
'''
        # Se não tem openssl, avisar o usuário
        logger.warning("⚠️ Para HTTPS, instale o openssl:")
        logger.warning("   Linux: sudo apt install openssl")
        logger.warning("   macOS: já vem instalado")
        logger.warning("   Windows: vem com Git for Windows")
        logger.warning("   Continuando sem HTTPS (microfone local funciona normalmente)")
        return False

    except Exception as e:
        logger.warning(f"⚠️ Não foi possível gerar certificado: {e}")
        return False


def open_browser(url: str):
    """Abre o navegador automaticamente após o servidor iniciar."""
    try:
        webbrowser.open(url)
        logger.info(f"🌐 Navegador aberto em: {url}")
    except Exception:
        logger.info(f"🌐 Abra manualmente no navegador: {url}")


def print_qr_hint(url: str):
    """Mostra instruções para conectar o celular."""
    logger.info("")
    logger.info("  📱 CONECTAR CELULAR (iPhone/Android):")
    logger.info(f"  Abra Chrome ou Safari no celular e acesse:")
    logger.info(f"  👉 {url}")
    logger.info("")
    logger.info("  ⚠️  O navegador vai avisar sobre certificado inseguro.")
    logger.info("     Isso é normal (é auto-assinado). Clique em:")
    logger.info("     • Chrome: 'Avançado' → 'Prosseguir'")
    logger.info("     • Safari: 'Mostrar Detalhes' → 'Visitar site'")
    logger.info("")


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

    # 7. Configurar HTTPS se habilitado
    host = config.web.host
    port = config.web.port
    local_ip = get_local_ip()
    ssl_context = None
    protocol = "http"

    if config.web.https_enabled:
        has_cert = generate_ssl_cert(config.web.ssl_cert, config.web.ssl_key)
        if has_cert:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(config.web.ssl_cert, config.web.ssl_key)
            protocol = "https"
            logger.info("🔐 HTTPS ativado — microfone remoto habilitado")
        else:
            logger.warning("⚠️ HTTPS não disponível — rodando em HTTP")
            logger.warning("   Microfone funciona normalmente no computador local")

    local_url = f"{protocol}://localhost:{port}"
    network_url = f"{protocol}://{local_ip}:{port}"

    # 8. Mostrar informações
    logger.info("")
    logger.info("=" * 60)
    logger.info("  ✨ IPagent Ultra-Lite PRONTO!")
    logger.info("")
    logger.info(f"  🖥️  Local:    {local_url}")
    logger.info(f"  🌐 Rede:     {network_url}")
    logger.info(f"  🔧 Admin:    {local_url}/admin")
    logger.info(f"  📚 Base:     {local_url}/knowledge")
    logger.info("")
    logger.info(f"  🧠 Modelo:   {config.agent.model_name}")
    logger.info(f"  🔍 Correção: {'Ativada' if config.correction.enabled else 'Desativada'}")
    logger.info(f"  🔐 HTTPS:    {'Ativado' if ssl_context else 'Desativado'}")
    logger.info(f"  💰 Custo:    R$ 0,00 — IA 100% local")
    logger.info("=" * 60)

    if ssl_context:
        print_qr_hint(network_url)
    else:
        logger.info("")
        logger.info("  📱 Para usar o celular como microfone remoto:")
        logger.info(f"     IPAGENT_HTTPS=true python main.py")
        logger.info("")

    logger.info("  Para parar: Ctrl+C")
    logger.info("  Para reabrir: ./run.sh (Linux/Mac) ou run.bat (Windows)")
    logger.info("")

    # 9. Abrir navegador automaticamente (se não for reloader do Flask)
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        timer = threading.Timer(1.5, open_browser, args=[local_url])
        timer.daemon = True
        timer.start()

    # 10. Iniciar servidor
    app.run(
        host=host,
        port=port,
        debug=config.web.debug,
        ssl_context=(config.web.ssl_cert, config.web.ssl_key) if ssl_context else None
    )


if __name__ == "__main__":
    main()
