#!/bin/bash
# ============================================
# IPagent — Script Único: Instala + Roda
# Se já instalado, apenas abre.
# 
# Uso: bash start.sh
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🏥 IPagent — Assistente Médico       ║${NC}"
echo -e "${BLUE}║     💰 Custo: R\$ 0,00 — IA 100% local   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ==========================================
# 1. Verificar Python
# ==========================================
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${YELLOW}⚠️  Python 3.8+ não encontrado. Instalando...${NC}"
    if command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y python3 python3-venv python3-pip
    elif command -v brew &>/dev/null; then
        brew install python@3.11
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-pip
    else
        echo "❌ Instale Python 3.8+ manualmente e rode novamente."
        exit 1
    fi
    PYTHON="python3"
fi

echo -e "${GREEN}✅ Python: $($PYTHON --version)${NC}"

# ==========================================
# 2. Verificar/Criar venv
# ==========================================
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo -e "${GREEN}✅ Ambiente virtual encontrado${NC}"
    FIRST_RUN=false
else
    echo -e "${YELLOW}📦 Primeira execução — criando ambiente...${NC}"
    $PYTHON -m venv venv
    FIRST_RUN=true
fi

source venv/bin/activate

# ==========================================
# 3. Instalar dependências (se necessário)
# ==========================================
if [ "$FIRST_RUN" = true ] || [ ! -f "venv/.deps_installed" ]; then
    echo -e "${YELLOW}📦 Instalando dependências...${NC}"
    pip install --upgrade pip -q
    pip install -r requirements.txt -q 2>&1 | tail -5
    touch venv/.deps_installed
    echo -e "${GREEN}✅ Dependências instaladas${NC}"
else
    echo -e "${GREEN}✅ Dependências OK${NC}"
fi

# ==========================================
# 4. Detectar GPU (opcional)
# ==========================================
if command -v nvidia-smi &>/dev/null; then
    echo -e "${GREEN}🎮 GPU NVIDIA detectada${NC}"
    export IPAGENT_GPU_LAYERS=35
fi

# ==========================================
# 5. Rodar IPagent!
# ==========================================
echo ""
echo -e "${GREEN}🚀 Iniciando IPagent...${NC}"
echo -e "${BLUE}   O navegador abrirá automaticamente.${NC}"
echo -e "${BLUE}   Para parar: Ctrl+C${NC}"
echo -e "${BLUE}   Para reabrir: bash start.sh${NC}"
echo ""

python main.py
