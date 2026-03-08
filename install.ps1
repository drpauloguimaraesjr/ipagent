# ============================================================================
#  IPagent — Instalador Automático (Windows PowerShell)
#  Assistente médico com IA local — 100% gratuito, sem consumo de tokens
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
    Write-Host "  ║   100% gratuito — sem consumo de tokens          ║" -ForegroundColor Cyan
    Write-Host "  ║                                                  ║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Info    { param($msg) Write-Host "  ℹ  $msg" -ForegroundColor Blue }
function Write-Success { param($msg) Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  ❌ $msg" -ForegroundColor Red }
function Write-Step    { param($n, $total, $msg) Write-Host "`n  [$n/$total] $msg" -ForegroundColor Cyan }

$TotalSteps = 7

# ── Detectar SO ──
Write-Banner
$arch = if ([System.Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
Write-Info "Sistema detectado: Windows ($arch)"

# ── Step 1: Verificar Python ──
Write-Step 1 $TotalSteps "Verificando Python..."

$pythonCmd = $null
$pythonVersion = $null
$usingEmbedded = $false

# Função para testar um comando python
function Test-Python {
    param($cmd)
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+\.\d+\.\d+)") {
            $v = $Matches[1]
            $parts = $v.Split(".")
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            if ($major -ge 3 -and $minor -ge 10) {
                return @{ Cmd = $cmd; Version = $v }
            }
        }
    } catch {}
    return $null
}

# Tenta python, python3
$result = Test-Python "python"
if (-not $result) { $result = Test-Python "python3" }

if ($result) {
    $pythonCmd = $result.Cmd
    $pythonVersion = $result.Version
    Write-Success "Python $pythonVersion encontrado"
} else {
    Write-Warn "Python não encontrado. Instalando automaticamente..."

    # Tentativa 1: winget
    $installed = $false
    $hasWinget = Get-Command winget -ErrorAction SilentlyContinue
    if ($hasWinget) {
        Write-Info "Tentando instalar via winget..."
        try {
            winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements -s winget 2>$null
            $env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:PATH"
            $result = Test-Python "python"
            if ($result) {
                $pythonCmd = $result.Cmd
                $pythonVersion = $result.Version
                $installed = $true
                Write-Success "Python $pythonVersion instalado via winget"
            }
        } catch {
            Write-Warn "winget falhou, tentando download direto..."
        }
    }

    # Tentativa 2: Download direto do Python (instalador oficial)
    if (-not $installed) {
        Write-Info "Baixando Python diretamente de python.org..."
        
        $pyInstallerUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        if ($arch -eq "x86") {
            $pyInstallerUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8.exe"
        }
        
        $pyInstaller = "$env:TEMP\python-installer.exe"
        
        Write-Info "Baixando instalador (~25 MB)..."
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $pyInstallerUrl -OutFile $pyInstaller -UseBasicParsing
            
            Write-Info "Instalando Python 3.12 (isso pode demorar ~1 min)..."
            Write-Info "O Python será adicionado ao PATH automaticamente."
            
            # Instalar silenciosamente com Add to PATH
            $installArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1"
            $process = Start-Process -FilePath $pyInstaller -ArgumentList $installArgs -Wait -PassThru
            
            if ($process.ExitCode -eq 0) {
                # Atualizar PATH
                $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
                $env:PATH = "$userPath;$env:PATH"
                
                # Adicionar caminhos comuns do Python
                $possiblePaths = @(
                    "$env:LOCALAPPDATA\Programs\Python\Python312",
                    "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts",
                    "$env:APPDATA\Python\Python312",
                    "$env:APPDATA\Python\Python312\Scripts"
                )
                foreach ($p in $possiblePaths) {
                    if (Test-Path $p) {
                        $env:PATH = "$p;$env:PATH"
                    }
                }
                
                # Testar novamente
                Start-Sleep -Seconds 2
                $result = Test-Python "python"
                if (-not $result) { $result = Test-Python "python3" }
                if (-not $result) { $result = Test-Python "py" }
                
                if ($result) {
                    $pythonCmd = $result.Cmd
                    $pythonVersion = $result.Version
                    $installed = $true
                    Write-Success "Python $pythonVersion instalado com sucesso!"
                }
            }
            
            # Limpar instalador
            Remove-Item $pyInstaller -Force -ErrorAction SilentlyContinue
            
        } catch {
            Write-Warn "Download direto falhou: $_"
        }
    }

    # Tentativa 3: Python embarcado (portable, sem instalação)
    if (-not $installed) {
        Write-Info "Usando Python embarcado (portable)..."
        
        $embeddedUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
        if ($arch -eq "x86") {
            $embeddedUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-win32.zip"
        }
        
        $embeddedDir = Join-Path (Get-Location) "python"
        $embeddedZip = "$env:TEMP\python-embedded.zip"
        
        try {
            Write-Info "Baixando Python portable (~12 MB)..."
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $embeddedUrl -OutFile $embeddedZip -UseBasicParsing
            
            Write-Info "Extraindo..."
            New-Item -ItemType Directory -Path $embeddedDir -Force | Out-Null
            Expand-Archive -Path $embeddedZip -DestinationPath $embeddedDir -Force
            
            # Habilitar pip no Python embarcado
            $pthFile = Get-ChildItem "$embeddedDir\python*._pth" | Select-Object -First 1
            if ($pthFile) {
                $content = Get-Content $pthFile.FullName
                $content = $content -replace "#import site", "import site"
                Set-Content $pthFile.FullName $content
            }
            
            # Baixar get-pip.py
            Write-Info "Instalando pip..."
            $getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
            $getPipPath = "$embeddedDir\get-pip.py"
            Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipPath -UseBasicParsing
            
            $embeddedPython = "$embeddedDir\python.exe"
            & $embeddedPython $getPipPath --no-warn-script-location 2>$null
            
            $env:PATH = "$embeddedDir;$embeddedDir\Scripts;$env:PATH"
            $pythonCmd = $embeddedPython
            $usingEmbedded = $true
            $installed = $true
            
            Write-Success "Python portable instalado em: $embeddedDir"
            
            # Limpar
            Remove-Item $embeddedZip -Force -ErrorAction SilentlyContinue
            
        } catch {
            Write-Err "Não foi possível instalar Python de nenhuma forma."
            Write-Host ""
            Write-Host "  Por favor, instale Python 3.10+ manualmente:" -ForegroundColor White
            Write-Host "    1. Acesse: https://www.python.org/downloads/" -ForegroundColor Gray
            Write-Host "    2. Baixe Python 3.12" -ForegroundColor Gray
            Write-Host "    3. IMPORTANTE: Marque 'Add Python to PATH'" -ForegroundColor Yellow
            Write-Host "    4. Execute este script novamente" -ForegroundColor Gray
            Write-Host ""
            Read-Host "Pressione Enter para sair"
            exit 1
        }
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
            # Download direto do Git portable
            Write-Info "Baixando Git portable..."
            $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.2/MinGit-2.47.1.2-64-bit.zip"
            $gitZip = "$env:TEMP\git-portable.zip"
            $gitDir = Join-Path (Get-Location) "git"
            
            try {
                Invoke-WebRequest -Uri $gitUrl -OutFile $gitZip -UseBasicParsing
                New-Item -ItemType Directory -Path $gitDir -Force | Out-Null
                Expand-Archive -Path $gitZip -DestinationPath $gitDir -Force
                $env:PATH = "$gitDir\cmd;$env:PATH"
                Remove-Item $gitZip -Force -ErrorAction SilentlyContinue
                Write-Success "Git portable instalado"
            } catch {
                Write-Err "Não foi possível instalar Git."
                Write-Err "Instale manualmente: https://git-scm.com/download/win"
                Read-Host "Pressione Enter para sair"
                exit 1
            }
        }
    }

    Write-Info "Clonando repositório..."
    git clone https://github.com/drpauloguimaraesjr/IPagent.git
    Set-Location IPagent
    Write-Success "Repositório clonado"
}

# ── Step 3: Criar ambiente virtual ──
Write-Step 3 $TotalSteps "Criando ambiente virtual Python..."

if ($usingEmbedded) {
    # Python embarcado não suporta venv nativamente, usar pip direto
    Write-Info "Usando Python portable (sem venv)"
    $pipCmd = Join-Path (Split-Path $pythonCmd) "Scripts\pip.exe"
    if (-not (Test-Path $pipCmd)) {
        $pipCmd = "pip"
    }
} else {
    if (Test-Path "venv") {
        Write-Info "Ambiente virtual existente encontrado"
    } else {
        & $pythonCmd -m venv venv
        Write-Success "Ambiente virtual criado"
    }
    # Ativar venv
    & .\venv\Scripts\Activate.ps1
}

# ── Step 4: Instalar dependências ──
Write-Step 4 $TotalSteps "Instalando dependências..."

if ($usingEmbedded) {
    & $pythonCmd -m pip install --upgrade pip -q 2>$null
    & $pythonCmd -m pip install -r requirements.txt -q
} else {
    pip install --upgrade pip -q 2>$null
    pip install -r requirements.txt -q
}
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
            if ($usingEmbedded) {
                & $pythonCmd -m pip install llama-cpp-python --force-reinstall --no-cache-dir `
                    -C cmake.args="-DGGML_CUDA=on" -q 2>$null
            } else {
                pip install llama-cpp-python --force-reinstall --no-cache-dir `
                    -C cmake.args="-DGGML_CUDA=on" -q 2>$null
            }
        } catch {
            Write-Warn "Não foi possível compilar com CUDA. Usando modo CPU."
            $gpuMode = "cpu"
        }
    }
} catch {
    Write-Info "Modo: CPU (funcional, mas mais lento)"
    Write-Info "Dica: Com GPU NVIDIA, as respostas são ~10x mais rápidas"
}

$gpuMode | Out-File -FilePath ".gpu_mode" -Encoding utf8 -NoNewline

# ── Step 6: Criar scripts de execução ──
Write-Step 6 $TotalSteps "Criando scripts de execução..."

# Criar diretórios de dados
$dirs = @("data\models", "data\knowledge", "data\consultations", "data\training_datasets", "data\uploads")
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

if ($usingEmbedded) {
    # Script para Python portable
    $pythonRelative = Resolve-Path -Relative $pythonCmd -ErrorAction SilentlyContinue
    if (-not $pythonRelative) { $pythonRelative = $pythonCmd }
    
    @"
# IPagent — Iniciar o servidor (Python Portable)
Set-Location `$PSScriptRoot

`$gpuLayers = -1
if (Test-Path ".gpu_mode") {
    `$mode = Get-Content ".gpu_mode" -Raw
    if (`$mode.Trim() -eq "cpu") { `$gpuLayers = 0 }
}

`$env:IPAGENT_GPU_LAYERS = `$gpuLayers
`$env:PATH = "`$PSScriptRoot\python;`$PSScriptRoot\python\Scripts;`$env:PATH"
Write-Host ""
Write-Host "  🧠 Iniciando IPagent..." -ForegroundColor Cyan
Write-Host "  Modo: `$(if (`$gpuLayers -eq 0) { 'CPU' } else { 'GPU' })" -ForegroundColor Gray
Write-Host "  💰 Custo: R`$ 0,00 (IA 100% local)" -ForegroundColor Gray
Write-Host ""
& "`$PSScriptRoot\python\python.exe" main.py
"@ | Out-File -FilePath "run.ps1" -Encoding utf8
} else {
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
Write-Host "  Modo: $(if ($gpuLayers -eq 0) { 'CPU' } else { 'GPU' })" -ForegroundColor Gray
Write-Host "  💰 Custo: R$ 0,00 (IA 100% local)" -ForegroundColor Gray
Write-Host ""
python main.py
'@ | Out-File -FilePath "run.ps1" -Encoding utf8
}

# Criar run.bat
@'
@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

:: Tentar venv primeiro, senão usa Python portable
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "python\python.exe" (
    set "PATH=%~dp0python;%~dp0python\Scripts;%PATH%"
)

set "GPU_LAYERS=-1"
if exist .gpu_mode (
    set /p MODE=<.gpu_mode
    if "%MODE%"=="cpu" set "GPU_LAYERS=0"
)

set IPAGENT_GPU_LAYERS=%GPU_LAYERS%
echo.
echo   IPagent - Iniciando...
echo   Custo: R$ 0,00 (IA 100%% local)
echo.
python main.py
pause
'@ | Out-File -FilePath "run.bat" -Encoding ascii

Write-Success "Scripts criados: run.ps1 e run.bat"

# ── Step 7: Verificar instalação ──
Write-Step 7 $TotalSteps "Verificando instalação..."

$testCmd = if ($usingEmbedded) { $pythonCmd } else { "python" }
try {
    $testResult = & $testCmd -c "
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
    import fitz
except ImportError as e:
    errors.append(f'PyMuPDF: {e}')
if errors:
    print('ERRO: ' + ' | '.join(errors))
    sys.exit(1)
else:
    print('OK')
" 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Todos os componentes verificados!"
    } else {
        Write-Warn "Alguns componentes com problemas: $testResult"
        Write-Warn "Tente: pip install -r requirements.txt"
    }
} catch {
    Write-Warn "Não foi possível verificar componentes"
}

# ── Finalização ──
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║                                                  ║" -ForegroundColor Green
Write-Host "  ║   ✨  Instalação concluída com sucesso!          ║" -ForegroundColor Green
Write-Host "  ║                                                  ║" -ForegroundColor Green
Write-Host "  ║   💰 Custo: R$ 0,00 — IA 100% local            ║" -ForegroundColor Green
Write-Host "  ║   🔒 Seus dados nunca saem do computador        ║" -ForegroundColor Green
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
