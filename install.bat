@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================================
::  IPagent — Instalador Automático (Windows)
::  Assistente médico com IA local
::
::  Uso: Abra o Prompt de Comando ou PowerShell e execute:
::    install.bat
:: ============================================================================

:: ── Cores ANSI (Windows 10+) ──
set "GREEN=[32m"
set "CYAN=[36m"
set "YELLOW=[33m"
set "RED=[31m"
set "BOLD=[1m"
set "DIM=[2m"
set "NC=[0m"

:: ── Banner ──
echo.
echo   %CYAN%%BOLD%╔══════════════════════════════════════════════════╗%NC%
echo   %CYAN%%BOLD%║                                                  ║%NC%
echo   %CYAN%%BOLD%║   IPagent Ultra-Lite — Instalador Windows        ║%NC%
echo   %CYAN%%BOLD%║   Assistente Medico com IA Local                 ║%NC%
echo   %CYAN%%BOLD%║                                                  ║%NC%
echo   %CYAN%%BOLD%╚══════════════════════════════════════════════════╝%NC%
echo.

:: ── Step 1: Verificar Python ──
echo   %CYAN%%BOLD%[1/6]%NC% %BOLD%Verificando Python...%NC%

set "PYTHON_CMD="

:: Tenta python primeiro (Windows geralmente usa "python" não "python3")
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=python"
    echo   %GREEN%OK%NC% Python !PY_VER! encontrado
    goto :check_py_version
)

where python3 >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python3 --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=python3"
    echo   %GREEN%OK%NC% Python !PY_VER! encontrado
    goto :check_py_version
)

:: Python não encontrado — tentar instalar via winget
echo   %YELLOW%AVISO%NC% Python nao encontrado. Tentando instalar...
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo   Instalando Python via winget...
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements -s winget
    if %errorlevel% equ 0 (
        :: Atualizar PATH
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
        set "PYTHON_CMD=python"
        echo   %GREEN%OK%NC% Python instalado com sucesso
        goto :after_python
    )
)

:: Fallback: instrucao manual
echo.
echo   %RED%ERRO%NC% Nao foi possivel instalar Python automaticamente.
echo.
echo   Por favor, instale Python 3.10+ manualmente:
echo     1. Acesse: https://www.python.org/downloads/
echo     2. Baixe a versao mais recente do Python 3.12
echo     3. IMPORTANTE: Marque "Add Python to PATH" durante a instalacao
echo     4. Execute este script novamente
echo.
pause
exit /b 1

:check_py_version
:: Verificar se a versão é >= 3.10
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if !PY_MAJOR! lss 3 (
    echo   %RED%ERRO%NC% Python !PY_VER! muito antigo. Precisa >= 3.10
    echo   Instale do site: https://www.python.org/downloads/
    pause
    exit /b 1
)
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 10 (
    echo   %RED%ERRO%NC% Python !PY_VER! muito antigo. Precisa >= 3.10
    echo   Instale do site: https://www.python.org/downloads/
    pause
    exit /b 1
)

:after_python

:: ── Step 2: Verificar código-fonte ──
echo.
echo   %CYAN%%BOLD%[2/6]%NC% %BOLD%Verificando codigo-fonte...%NC%

if exist "main.py" if exist "config.py" if exist "core" (
    echo   %GREEN%OK%NC% Codigo-fonte encontrado no diretorio atual
    goto :setup_venv
)

:: Verificar git e clonar
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo   %YELLOW%AVISO%NC% Git nao encontrado. Tentando instalar...
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        winget install Git.Git --accept-package-agreements --accept-source-agreements -s winget
        set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
    ) else (
        echo   %RED%ERRO%NC% Instale Git manualmente: https://git-scm.com/download/win
        pause
        exit /b 1
    )
)

echo   Clonando repositorio...
git clone https://github.com/drpauloguimaraesjr/IPagent.git
cd IPagent
echo   %GREEN%OK%NC% Repositorio clonado

:setup_venv
:: ── Step 3: Criar ambiente virtual ──
echo.
echo   %CYAN%%BOLD%[3/6]%NC% %BOLD%Criando ambiente virtual Python...%NC%

if exist "venv" (
    echo   Ambiente virtual existente encontrado
) else (
    !PYTHON_CMD! -m venv venv
    echo   %GREEN%OK%NC% Ambiente virtual criado
)

:: Ativar venv
call venv\Scripts\activate.bat

:: ── Step 4: Instalar dependências ──
echo.
echo   %CYAN%%BOLD%[4/6]%NC% %BOLD%Instalando dependencias...%NC%

pip install --upgrade pip -q 2>nul
pip install -r requirements.txt -q
echo   %GREEN%OK%NC% Todas as dependencias instaladas

:: ── Step 5: Verificar GPU ──
echo.
echo   %CYAN%%BOLD%[5/6]%NC% %BOLD%Detectando aceleracao por hardware...%NC%

set "GPU_MODE=cpu"

:: Verificar NVIDIA GPU
where nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    nvidia-smi >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=*" %%g in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do (
            echo   %GREEN%OK%NC% GPU NVIDIA detectada: %%g
        )
        set "GPU_MODE=nvidia"
        echo   Reinstalando llama-cpp-python com suporte CUDA...
        pip install llama-cpp-python --force-reinstall --no-cache-dir -C cmake.args="-DGGML_CUDA=on" -q 2>nul
        if %errorlevel% neq 0 (
            echo   %YELLOW%AVISO%NC% Nao foi possivel compilar com CUDA. Usando modo CPU.
            set "GPU_MODE=cpu"
        )
    ) else (
        echo   %YELLOW%AVISO%NC% GPU NVIDIA detectada, mas driver nao esta ativo
        echo   Para usar GPU: atualize o driver em https://www.nvidia.com/drivers/
    )
) else (
    echo   Modo: %BOLD%CPU%NC% ^(funcional, mas mais lento^)
    echo   Dica: Com GPU NVIDIA, as respostas sao ~10x mais rapidas
)

:: Salvar configuração GPU
echo %GPU_MODE%> .gpu_mode

:: ── Step 6: Criar scripts de execução ──
echo.
echo   %CYAN%%BOLD%[6/6]%NC% %BOLD%Criando scripts de execucao...%NC%

:: Criar diretórios de dados
if not exist "data\models" mkdir data\models
if not exist "data\knowledge" mkdir data\knowledge
if not exist "data\consultations" mkdir data\consultations
if not exist "data\training_datasets" mkdir data\training_datasets
if not exist "data\uploads" mkdir data\uploads

:: Criar run.bat
(
echo @echo off
echo chcp 65001 ^>nul 2^>^&1
echo cd /d "%%~dp0"
echo call venv\Scripts\activate.bat
echo.
echo set "GPU_LAYERS=-1"
echo if exist .gpu_mode ^(
echo     set /p MODE=^<.gpu_mode
echo     if "%%MODE%%"=="cpu" set "GPU_LAYERS=0"
echo ^)
echo.
echo set IPAGENT_GPU_LAYERS=%%GPU_LAYERS%%
echo echo.
echo echo   IPagent - Iniciando...
echo echo   Modo GPU: %%GPU_LAYERS%%
echo echo.
echo python main.py
echo pause
) > run.bat

echo   %GREEN%OK%NC% Script de execucao criado: %BOLD%run.bat%NC%

:: ── Finalização ──
echo.
echo   %GREEN%%BOLD%╔══════════════════════════════════════════════════╗%NC%
echo   %GREEN%%BOLD%║                                                  ║%NC%
echo   %GREEN%%BOLD%║   Instalacao concluida com sucesso!               ║%NC%
echo   %GREEN%%BOLD%║                                                  ║%NC%
echo   %GREEN%%BOLD%╚══════════════════════════════════════════════════╝%NC%
echo.
echo   %BOLD%Para iniciar o IPagent:%NC%
echo.
echo     %CYAN%run.bat%NC%
echo.
echo   %DIM%Ou manualmente:%NC%
echo     %DIM%venv\Scripts\activate.bat%NC%
echo     %DIM%python main.py%NC%
echo.
echo   %BOLD%Acesse:%NC% %CYAN%http://localhost:5000%NC%
echo.
echo   Na primeira execucao, o modelo de IA ^(~2 GB^) sera
echo   baixado automaticamente. Depois disso, inicia em segundos.
echo.

set /p START="  Deseja iniciar o IPagent agora? [S/n] "
if /i not "!START!"=="n" (
    call run.bat
)

endlocal
