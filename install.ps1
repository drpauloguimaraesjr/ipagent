# ============================================================================
#  IPagent — Instalador Automático (Windows PowerShell)
#  Assistente médico com IA local
#
#  Uso (PowerShell):
#    irm https://raw.githubusercontent.com/drpauloguimaraesjr/IPagent/main/install.ps1 | iex
#  Ou:
#    git clone https://github.com/drpauloguimaraesjr/IPagent.git; cd IPagent; .\install.ps1
# ============================================================================

$ErrorActionPreference = "Stop"

# ── Funções de UI ──
function Write-Banner {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║                                                  ║" -ForegroundColor Cyan
    Write-Host "  ║   🧠  IPagent Ultra-Lite — Instalador           ║" -ForegroundColor Cyan
    Write-Host "  ║   Assistente Médico com IA Local                 ║" -ForegroundColor Cyan
    Write-Host "  ║                                                  ║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Info    { param($msg) Write-Host "  ℹ  $msg" -ForegroundColor Blue }
function Write-Success { param($msg) Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  ❌ $msg" -ForegroundColor Red }
function Write-Step    { param($n, $total, $msg) Write-Host "`n  [$n/$total] $msg" -ForegroundColor Cyan }

$TotalSteps = 6

# ── Detectar SO ──
Write-Banner
$arch = if ([System.Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
Write-Info "Sistema detectado: Windows ($arch)"

# ── Step 1: Verificar Python ──
Write-Step 1 $TotalSteps "Verificando Python..."

$pythonCmd = $null
$pythonVersion = $null

# Tenta python
try {
    $ver = & python --version 2>&1
    if ($ver -match "Python (\d+\.\d+\.\d+)") {
        $pythonVersion = $Matches[1]
        $parts = $pythonVersion.Split(".")
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        if ($major -ge 3 -and $minor -ge 10) {
            $pythonCmd = "python"
            Write-Success "Python $pythonVersion encontrado"
        } else {
            Write-Warn "Python $pythonVersion encontrado, mas precisa >= 3.10"
        }
    }
} catch {}

# Tenta python3
if (-not $pythonCmd) {
    try {
        $ver = & python3 --version 2>&1
        if ($ver -match "Python (\d+\.\d+\.\d+)") {
            $pythonVersion = $Matches[1]
            $parts = $pythonVersion.Split(".")
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            if ($major -ge 3 -and $minor -ge 10) {
                $pythonCmd = "python3"
                Write-Success "Python $pythonVersion encontrado"
            }
        }
    } catch {}
}

# Instalar Python se necessário
if (-not $pythonCmd) {
    Write-Warn "Python não encontrado. Tentando instalar..."

    # Tenta winget
    $hasWinget = Get-Command winget -ErrorAction SilentlyContinue
    if ($hasWinget) {
        Write-Info "Instalando Python via winget..."
        winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements -s winget
        
        # Atualizar PATH
        $env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:PATH"
        $pythonCmd = "python"
        Write-Success "Python instalado com sucesso"
    } else {
        Write-Err "Não foi possível instalar Python automaticamente."
        Write-Host ""
        Write-Host "  Por favor, instale Python 3.10+ manualmente:" -ForegroundColor White
        Write-Host "    1. Acesse: https://www.python.org/downloads/" -ForegroundColor Gray
        Write-Host "    2. Baixe a versão mais recente do Python 3.12" -ForegroundColor Gray
        Write-Host "    3. IMPORTANTE: Marque 'Add Python to PATH'" -ForegroundColor Yellow
        Write-Host "    4. Execute este script novamente" -ForegroundColor Gray
        Write-Host ""
        Read-Host "Pressione Enter para sair"
        exit 1
    }
}

# ── Step 2: Verificar código-fonte ──
Write-Step 2 $TotalSteps "Verificando código-fonte..."

if ((Test-Path "main.py") -and (Test-Path "config.py") -and (Test-Path "core")) {
    Write-Success "Código-fonte encontrado no diretório atual"
} else {
    # Verificar git
    $hasGit = Get-Command git -ErrorAction SilentlyContinue
    if (-not $hasGit) {
        Write-Warn "Git não encontrado. Tentando instalar..."
        $hasWinget = Get-Command winget -ErrorAction SilentlyContinue
        if ($hasWinget) {
            winget install Git.Git --accept-package-agreements --accept-source-agreements -s winget
            $env:PATH = "$env:ProgramFiles\Git\cmd;$env:PATH"
        } else {
            Write-Err "Instale Git manualmente: https://git-scm.com/download/win"
            Read-Host "Pressione Enter para sair"
            exit 1
        }
    }

    Write-Info "Clonando repositório..."
    git clone https://github.com/drpauloguimaraesjr/IPagent.git
    Set-Location IPagent
    Write-Success "Repositório clonado"
}

# ── Step 3: Criar ambiente virtual ──
Write-Step 3 $TotalSteps "Criando ambiente virtual Python..."

if (Test-Path "venv") {
    Write-Info "Ambiente virtual existente encontrado"
} else {
    & $pythonCmd -m venv venv
    Write-Success "Ambiente virtual criado"
}

# Ativar venv
& .\venv\Scripts\Activate.ps1

# ── Step 4: Instalar dependências ──
Write-Step 4 $TotalSteps "Instalando dependências..."

pip install --upgrade pip -q 2>$null
pip install -r requirements.txt -q
Write-Success "Todas as dependências instaladas"

# ── Step 5: Verificar GPU ──
Write-Step 5 $TotalSteps "Detectando aceleração por hardware..."

$gpuMode = "cpu"

try {
    $nvidiaSmi = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
    if ($LASTEXITCODE -eq 0 -and $nvidiaSmi) {
        Write-Success "GPU NVIDIA detectada: $nvidiaSmi"
        $gpuMode = "nvidia"
        
        Write-Info "Reinstalando llama-cpp-python com suporte CUDA..."
        try {
            pip install llama-cpp-python --force-reinstall --no-cache-dir `
                -C cmake.args="-DGGML_CUDA=on" -q 2>$null
        } catch {
            Write-Warn "Não foi possível compilar com CUDA. Usando modo CPU."
            $gpuMode = "cpu"
        }
    }
} catch {
    Write-Info "Modo: CPU (funcional, mas mais lento)"
    Write-Info "Dica: Com GPU NVIDIA, as respostas são ~10x mais rápidas"
}

# Salvar configuração GPU
$gpuMode | Out-File -FilePath ".gpu_mode" -Encoding utf8 -NoNewline

# ── Step 6: Criar scripts de execução ──
Write-Step 6 $TotalSteps "Criando scripts de execução..."

# Criar diretórios de dados
$dirs = @("data\models", "data\knowledge", "data\consultations", "data\training_datasets", "data\uploads")
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

# Criar run.ps1
@'
# IPagent — Iniciar o servidor
Set-Location $PSScriptRoot
& .\venv\Scripts\Activate.ps1

$gpuLayers = -1
if (Test-Path ".gpu_mode") {
    $mode = Get-Content ".gpu_mode" -Raw
    if ($mode.Trim() -eq "cpu") { $gpuLayers = 0 }
}

$env:IPAGENT_GPU_LAYERS = $gpuLayers
Write-Host ""
Write-Host "  🧠 Iniciando IPagent..." -ForegroundColor Cyan
Write-Host "  Modo GPU: $(if ($gpuLayers -eq 0) { 'CPU' } else { 'GPU' })" -ForegroundColor Gray
Write-Host ""
python main.py
'@ | Out-File -FilePath "run.ps1" -Encoding utf8

# Criar run.bat (para quem preferir cmd)
@'
@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
call venv\Scripts\activate.bat

set "GPU_LAYERS=-1"
if exist .gpu_mode (
    set /p MODE=<.gpu_mode
    if "%MODE%"=="cpu" set "GPU_LAYERS=0"
)

set IPAGENT_GPU_LAYERS=%GPU_LAYERS%
echo.
echo   IPagent - Iniciando...
echo.
python main.py
pause
'@ | Out-File -FilePath "run.bat" -Encoding ascii

Write-Success "Scripts criados: run.ps1 e run.bat"

# ── Finalização ──
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║                                                  ║" -ForegroundColor Green
Write-Host "  ║   ✨  Instalação concluída com sucesso!          ║" -ForegroundColor Green
Write-Host "  ║                                                  ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Para iniciar o IPagent:" -ForegroundColor White
Write-Host ""
Write-Host "    .\run.ps1" -ForegroundColor Cyan
Write-Host "    (ou run.bat no Prompt de Comando)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Acesse: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "  📝 Na primeira execução, o modelo de IA (~2 GB) será" -ForegroundColor Gray
Write-Host "     baixado automaticamente." -ForegroundColor Gray
Write-Host ""

$start = Read-Host "  Deseja iniciar o IPagent agora? [S/n]"
if ($start -ne "n" -and $start -ne "N") {
    & .\run.ps1
}
