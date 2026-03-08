#!/usr/bin/env bash
# ============================================================================
#  IPagent — Instalador Automático (Linux / macOS)
#  Assistente médico com IA local — 100% gratuito, sem consumo de tokens
#
#  Uso:
#    curl -fsSL https://raw.githubusercontent.com/drpauloguimaraesjr/IPagent/main/install.sh | bash
#  Ou:
#    git clone https://github.com/drpauloguimaraesjr/IPagent.git && cd IPagent && bash install.sh
# ============================================================================

set -e

# ── Cores ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# ── Funções de UI ──
banner() {
    echo ""
    echo -e "${CYAN}${BOLD}"
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║                                                      ║"
    echo "  ║   🧠  IPagent Ultra-Lite — Instalador                ║"
    echo "  ║   Assistente Médico com IA Local                     ║"
    echo "  ║   100% gratuito — sem consumo de tokens              ║"
    echo "  ║                                                      ║"
    echo "  ╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

info()    { echo -e "  ${BLUE}ℹ${NC}  $1"; }
success() { echo -e "  ${GREEN}✅${NC} $1"; }
warn()    { echo -e "  ${YELLOW}⚠️${NC}  $1"; }
error()   { echo -e "  ${RED}❌${NC} $1"; }
step()    { echo -e "\n  ${CYAN}${BOLD}[$1/$TOTAL_STEPS]${NC} ${BOLD}$2${NC}"; }

TOTAL_STEPS=7
INSTALL_OLLAMA=false

# ── Detectar SO ──
detect_os() {
    case "$(uname -s)" in
        Linux*)   OS="linux";;
        Darwin*)  OS="macos";;
        CYGWIN*|MINGW*|MSYS*)  OS="windows";;
        *)        OS="unknown";;
    esac

    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64|amd64) ARCH="x64";;
        arm64|aarch64) ARCH="arm64";;
    esac

    info "Sistema detectado: ${BOLD}$OS ($ARCH)${NC}"
}

# ── Perguntar sobre Ollama ──
ask_ollama() {
    echo ""
    echo -e "  ${BOLD}O IPagent funciona de 2 formas:${NC}"
    echo -e "  ${GREEN}1)${NC} ${BOLD}Embutido${NC} — IA roda direto no Python (padrão, mais simples)"
    echo -e "  ${GREEN}2)${NC} ${BOLD}Com Ollama${NC} — Servidor de IA separado (mais rápido, mais modelos)"
    echo ""
    echo -e "  ${DIM}Ambas são 100% locais e gratuitas. Sem API, sem tokens, sem nuvem.${NC}"
    echo ""
    read -p "  Deseja instalar o Ollama também? [s/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        INSTALL_OLLAMA=true
        TOTAL_STEPS=8
        success "Ollama será instalado"
    else
        info "Usando modo embutido (sem Ollama)"
    fi
}

# ── Verificar/instalar Python ──
check_python() {
    step 1 "Verificando Python..."

    PYTHON_CMD=""

    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    fi

    if [ -z "$PYTHON_CMD" ]; then
        warn "Python não encontrado. Tentando instalar..."
        install_python
    else
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            success "Python $($PYTHON_CMD --version 2>&1) encontrado"
        else
            warn "Python $PYTHON_VERSION encontrado, mas precisa >= 3.10"
            install_python
        fi
    fi
}

install_python() {
    case "$OS" in
        linux)
            if command -v apt-get &>/dev/null; then
                info "Instalando Python via apt..."
                sudo apt-get update -qq
                sudo apt-get install -y -qq python3 python3-pip python3-venv
            elif command -v dnf &>/dev/null; then
                info "Instalando Python via dnf..."
                sudo dnf install -y python3 python3-pip
            elif command -v pacman &>/dev/null; then
                info "Instalando Python via pacman..."
                sudo pacman -Sy --noconfirm python python-pip
            else
                error "Gerenciador de pacotes não reconhecido."
                error "Instale Python 3.10+ manualmente: https://www.python.org/downloads/"
                exit 1
            fi
            PYTHON_CMD="python3"
            ;;
        macos)
            if command -v brew &>/dev/null; then
                info "Instalando Python via Homebrew..."
                brew install python@3.12
                PYTHON_CMD="python3"
            else
                warn "Homebrew não encontrado. Instalando Homebrew primeiro..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

                if [ "$ARCH" = "arm64" ]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                else
                    eval "$(/usr/local/bin/brew shellenv)"
                fi

                brew install python@3.12
                PYTHON_CMD="python3"
            fi
            ;;
        *)
            error "Instale Python 3.10+ manualmente: https://www.python.org/downloads/"
            exit 1
            ;;
    esac
    success "Python instalado com sucesso"
}

# ── Verificar Git e clonar se necessário ──
check_git_and_clone() {
    step 2 "Verificando código-fonte..."

    if [ -f "main.py" ] && [ -f "config.py" ] && [ -d "core" ]; then
        success "Código-fonte encontrado no diretório atual"
        return
    fi

    if ! command -v git &>/dev/null; then
        warn "Git não encontrado. Instalando..."
        case "$OS" in
            linux)
                if command -v apt-get &>/dev/null; then
                    sudo apt-get install -y -qq git
                elif command -v dnf &>/dev/null; then
                    sudo dnf install -y git
                elif command -v pacman &>/dev/null; then
                    sudo pacman -Sy --noconfirm git
                fi
                ;;
            macos)
                xcode-select --install 2>/dev/null || brew install git
                ;;
        esac
    fi

    info "Clonando repositório..."
    git clone https://github.com/drpauloguimaraesjr/IPagent.git
    cd IPagent
    success "Repositório clonado"
}

# ── Criar ambiente virtual e instalar dependências ──
setup_venv() {
    step 3 "Criando ambiente virtual Python..."

    if [ -d "venv" ]; then
        info "Ambiente virtual existente encontrado"
    else
        $PYTHON_CMD -m venv venv
        success "Ambiente virtual criado"
    fi

    # Ativar venv
    source venv/bin/activate

    step 4 "Instalando dependências..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    success "Todas as dependências instaladas"
}

# ── Verificar GPU ──
check_gpu() {
    step 5 "Detectando aceleração por hardware..."

    GPU_MODE="cpu"
    GPU_INFO=""

    case "$OS" in
        linux)
            if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
                GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "")
                if [ -n "$GPU_INFO" ]; then
                    GPU_MODE="nvidia"
                    success "GPU NVIDIA detectada: ${BOLD}$GPU_INFO${NC}"
                    info "Reinstalando llama-cpp-python com suporte CUDA..."
                    pip install llama-cpp-python --force-reinstall --no-cache-dir \
                        -C cmake.args="-DGGML_CUDA=on" -q 2>/dev/null || {
                        warn "Não foi possível compilar com CUDA. Usando modo CPU."
                        GPU_MODE="cpu"
                    }
                fi
            elif lspci 2>/dev/null | grep -qi nvidia; then
                warn "GPU NVIDIA detectada no hardware, mas driver não está ativo"
                warn "Para usar GPU: sudo apt install nvidia-driver-XXX && sudo reboot"
                GPU_MODE="cpu"
            fi
            ;;
        macos)
            if [ "$ARCH" = "arm64" ]; then
                GPU_MODE="metal"
                success "Apple Silicon detectado — aceleração Metal disponível"
                info "Reinstalando llama-cpp-python com suporte Metal..."
                pip install llama-cpp-python --force-reinstall --no-cache-dir \
                    -C cmake.args="-DGGML_METAL=on" -q 2>/dev/null || {
                    warn "Não foi possível compilar com Metal. Usando modo CPU."
                    GPU_MODE="cpu"
                }
            else
                info "Mac Intel — usando modo CPU"
                GPU_MODE="cpu"
            fi
            ;;
    esac

    if [ "$GPU_MODE" = "cpu" ]; then
        info "Modo: ${BOLD}CPU${NC} (funciona, mas será mais lento)"
        info "Dica: Com GPU NVIDIA/Apple Silicon, as respostas são ~10x mais rápidas"
    fi

    echo "$GPU_MODE" > .gpu_mode
}

# ── Instalar Ollama (opcional) ──
install_ollama() {
    if [ "$INSTALL_OLLAMA" = false ]; then
        return
    fi

    step 6 "Instalando Ollama..."

    if command -v ollama &>/dev/null; then
        success "Ollama já está instalado: $(ollama --version 2>/dev/null || echo 'versão desconhecida')"
    else
        info "Baixando e instalando Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        success "Ollama instalado com sucesso"
    fi

    # Baixar modelo médico recomendado
    info "Baixando modelo recomendado para uso médico..."
    info "Isso pode demorar alguns minutos (~2-5 GB)..."
    ollama pull qwen2.5:7b 2>/dev/null || {
        warn "Não foi possível baixar o modelo agora."
        warn "Execute depois: ollama pull qwen2.5:7b"
    }

    success "Ollama configurado!"
    echo ""
    echo -e "  ${DIM}Para usar o IPagent com Ollama, defina:${NC}"
    echo -e "  ${CYAN}export IPAGENT_OLLAMA_HOST=http://localhost:11434${NC}"
}

# ── Criar diretórios e script de execução ──
create_launcher() {
    local step_num=6
    if [ "$INSTALL_OLLAMA" = true ]; then
        step_num=7
    fi

    step $step_num "Criando scripts de execução..."

    # Criar diretórios de dados
    mkdir -p data/models data/knowledge data/consultations data/training_datasets data/uploads

    # Criar script de execução
    cat > run.sh << 'LAUNCHER'
#!/usr/bin/env bash
# IPagent — Iniciar o servidor
# 100% local. Sem consumo de tokens. Sem API paga.
cd "$(dirname "$0")"
source venv/bin/activate

# Detectar modo GPU
GPU_LAYERS=-1
if [ -f .gpu_mode ]; then
    MODE=$(cat .gpu_mode)
    if [ "$MODE" = "cpu" ]; then
        GPU_LAYERS=0
    fi
fi

export IPAGENT_GPU_LAYERS=$GPU_LAYERS
echo ""
echo "🧠 Iniciando IPagent..."
echo "   Modo: $([ "$GPU_LAYERS" = "0" ] && echo "CPU" || echo "GPU")"
echo "   💰 Custo: R$ 0,00 (IA 100% local)"
echo ""
python main.py
LAUNCHER
    chmod +x run.sh

    success "Script de execução criado: ${BOLD}./run.sh${NC}"
}

# ── Verificação final ──
verify_installation() {
    local step_num=7
    if [ "$INSTALL_OLLAMA" = true ]; then
        step_num=8
    fi

    step $step_num "Verificando instalação..."

    # Testar imports críticos
    source venv/bin/activate
    $PYTHON_CMD -c "
import sys
errors = []
try:
    from llama_cpp import Llama
except ImportError as e:
    errors.append(f'llama-cpp-python: {e}')
try:
    import flask
except ImportError as e:
    errors.append(f'Flask: {e}')
try:
    import fitz  # PyMuPDF
except ImportError as e:
    errors.append(f'PyMuPDF: {e}')
try:
    from huggingface_hub import hf_hub_download
except ImportError as e:
    errors.append(f'huggingface-hub: {e}')

if errors:
    print('ERRORS:' + '|'.join(errors))
    sys.exit(1)
else:
    print('OK')
" 2>/dev/null

    if [ $? -eq 0 ]; then
        success "Todos os componentes verificados!"
    else
        warn "Alguns componentes podem ter problemas. Tente: pip install -r requirements.txt"
    fi
}

# ── Finalização ──
finish() {
    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║                                                      ║"
    echo "  ║   ✨  Instalação concluída com sucesso!              ║"
    echo "  ║                                                      ║"
    echo "  ║   💰 Custo de uso: R\$ 0,00 — IA 100% local         ║"
    echo "  ║   🔒 Seus dados nunca saem do computador            ║"
    echo "  ║                                                      ║"
    echo "  ╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "  ${BOLD}Para iniciar o IPagent:${NC}"
    echo ""
    echo -e "    ${CYAN}./run.sh${NC}"
    echo ""
    echo -e "  ${DIM}Ou manualmente:${NC}"
    echo -e "    ${DIM}source venv/bin/activate${NC}"
    echo -e "    ${DIM}python main.py${NC}"
    echo ""
    echo -e "  ${BOLD}Acesse:${NC} ${CYAN}http://localhost:5000${NC}"
    echo ""
    echo -e "  ${DIM}📝 Na primeira execução, o modelo de IA (~2 GB) será${NC}"
    echo -e "  ${DIM}   baixado automaticamente. Depois disso, inicia em segundos.${NC}"
    echo ""

    read -p "  Deseja iniciar o IPagent agora? [S/n] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        ./run.sh
    fi
}

# ── MAIN ──
banner
detect_os
ask_ollama
check_python
check_git_and_clone
setup_venv
check_gpu
install_ollama
create_launcher
verify_installation
finish
