@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================================
::  IPagent — Instalador Automático (Windows CMD)
::  Assistente médico com IA local — 100%% gratuito, sem consumo de tokens
::
::  Uso: Abra o Prompt de Comando e execute:
::    install.bat
:: ============================================================================

echo.
echo   ╔══════════════════════════════════════════════════╗
echo   ║                                                  ║
echo   ║   IPagent Ultra-Lite — Instalador Windows        ║
echo   ║   Assistente Medico com IA Local                 ║
echo   ║   100%% gratuito — sem consumo de tokens          ║
echo   ║                                                  ║
echo   ╚══════════════════════════════════════════════════╝
echo.

:: ── Step 1: Verificar Python ──
echo   [1/7] Verificando Python...

set "PYTHON_CMD="
set "USING_EMBEDDED="

:: Tenta python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=python"
    goto :check_py_version
)

:: Tenta python3
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python3 --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=python3"
    goto :check_py_version
)

:: Python não encontrado
goto :install_python

:check_py_version
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if !PY_MAJOR! lss 3 goto :install_python
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 10 goto :install_python
echo   OK Python !PY_VER! encontrado
goto :after_python

:install_python
echo   Python nao encontrado ou versao antiga. Instalando automaticamente...

:: Tentativa 1: winget
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo   Tentando instalar via winget...
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements -s winget >nul 2>&1
    if %errorlevel% equ 0 (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
        set "PYTHON_CMD=python"
        echo   OK Python instalado via winget
        goto :after_python
    )
)

:: Tentativa 2: Download direto do instalador Python
echo   Baixando Python de python.org...

set "PY_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
set "PY_INSTALLER=%TEMP%\python-installer.exe"

:: Usar PowerShell para download (sempre disponível no Windows 10+)
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%' -UseBasicParsing" 2>nul

if exist "%PY_INSTALLER%" (
    echo   Instalando Python 3.12 (pode demorar ~1 minuto)...
    "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
    if %errorlevel% equ 0 (
        :: Atualizar PATH
        for /f "tokens=*" %%p in ('powershell -Command "[Environment]::GetEnvironmentVariable('PATH','User')"') do set "PATH=%%p;%PATH%"
        set "PYTHON_CMD=python"
        del "%PY_INSTALLER%" 2>nul
        echo   OK Python 3.12 instalado com sucesso!
        goto :after_python
    )
    del "%PY_INSTALLER%" 2>nul
)

:: Tentativa 3: Python embarcado (portable)
echo   Usando Python portable (sem necessidade de instalacao)...

set "EMBED_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
set "EMBED_ZIP=%TEMP%\python-embedded.zip"
set "EMBED_DIR=%CD%\python"

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%EMBED_URL%' -OutFile '%EMBED_ZIP%' -UseBasicParsing" 2>nul

if exist "%EMBED_ZIP%" (
    echo   Extraindo Python portable...
    if not exist "%EMBED_DIR%" mkdir "%EMBED_DIR%"
    powershell -Command "Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%EMBED_DIR%' -Force" 2>nul
    
    :: Habilitar pip no Python embarcado
    powershell -Command "$f = Get-ChildItem '%EMBED_DIR%\python*._pth' | Select-Object -First 1; if($f){$c = Get-Content $f.FullName; $c = $c -replace '#import site','import site'; Set-Content $f.FullName $c}" 2>nul
    
    :: Instalar pip
    echo   Instalando pip...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%EMBED_DIR%\get-pip.py' -UseBasicParsing" 2>nul
    "%EMBED_DIR%\python.exe" "%EMBED_DIR%\get-pip.py" --no-warn-script-location >nul 2>&1
    
    set "PATH=%EMBED_DIR%;%EMBED_DIR%\Scripts;%PATH%"
    set "PYTHON_CMD=%EMBED_DIR%\python.exe"
    set "USING_EMBEDDED=1"
    del "%EMBED_ZIP%" 2>nul
    echo   OK Python portable pronto em: %EMBED_DIR%
    goto :after_python
)

:: Nenhuma tentativa funcionou
echo.
echo   ERRO: Nao foi possivel instalar Python automaticamente.
echo.
echo   Por favor, instale Python 3.10+ manualmente:
echo     1. Acesse: https://www.python.org/downloads/
echo     2. Baixe Python 3.12
echo     3. IMPORTANTE: Marque "Add Python to PATH"
echo     4. Execute este script novamente
echo.
pause
exit /b 1

:after_python

:: ── Step 2: Verificar código-fonte ──
echo.
echo   [2/7] Verificando codigo-fonte...

if exist "main.py" if exist "config.py" if exist "core" (
    echo   OK Codigo-fonte encontrado
    goto :setup_venv
)

:: Verificar git e clonar
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo   Git nao encontrado. Tentando instalar...
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        winget install Git.Git --accept-package-agreements --accept-source-agreements -s winget >nul 2>&1
        set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
    ) else (
        :: Download Git portable
        echo   Baixando Git portable...
        set "GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.2/MinGit-2.47.1.2-64-bit.zip"
        set "GIT_ZIP=%TEMP%\git-portable.zip"
        set "GIT_DIR=%CD%\git"
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!GIT_URL!' -OutFile '!GIT_ZIP!' -UseBasicParsing" 2>nul
        if exist "!GIT_ZIP!" (
            if not exist "!GIT_DIR!" mkdir "!GIT_DIR!"
            powershell -Command "Expand-Archive -Path '!GIT_ZIP!' -DestinationPath '!GIT_DIR!' -Force" 2>nul
            set "PATH=!GIT_DIR!\cmd;%PATH%"
            del "!GIT_ZIP!" 2>nul
        ) else (
            echo   ERRO: Instale Git manualmente: https://git-scm.com/download/win
            pause
            exit /b 1
        )
    )
)

echo   Clonando repositorio...
git clone https://github.com/drpauloguimaraesjr/IPagent.git
cd IPagent
echo   OK Repositorio clonado

:setup_venv
:: ── Step 3: Criar ambiente virtual ──
echo.
echo   [3/7] Criando ambiente virtual Python...

if defined USING_EMBEDDED (
    echo   Usando Python portable ^(sem venv^)
    goto :install_deps
)

if exist "venv" (
    echo   Ambiente virtual existente encontrado
) else (
    !PYTHON_CMD! -m venv venv
    echo   OK Ambiente virtual criado
)
call venv\Scripts\activate.bat

:install_deps
:: ── Step 4: Instalar dependências ──
echo.
echo   [4/7] Instalando dependencias...

if defined USING_EMBEDDED (
    "!PYTHON_CMD!" -m pip install --upgrade pip -q 2>nul
    "!PYTHON_CMD!" -m pip install -r requirements.txt -q
) else (
    pip install --upgrade pip -q 2>nul
    pip install -r requirements.txt -q
)
echo   OK Todas as dependencias instaladas

:: ── Step 5: Verificar GPU ──
echo.
echo   [5/7] Detectando aceleracao por hardware...

set "GPU_MODE=cpu"

where nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    nvidia-smi >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=*" %%g in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do (
            echo   OK GPU NVIDIA detectada: %%g
        )
        set "GPU_MODE=nvidia"
        echo   Reinstalando llama-cpp-python com suporte CUDA...
        if defined USING_EMBEDDED (
            "!PYTHON_CMD!" -m pip install llama-cpp-python --force-reinstall --no-cache-dir -C cmake.args="-DGGML_CUDA=on" -q 2>nul
        ) else (
            pip install llama-cpp-python --force-reinstall --no-cache-dir -C cmake.args="-DGGML_CUDA=on" -q 2>nul
        )
        if %errorlevel% neq 0 (
            echo   AVISO: Nao foi possivel compilar com CUDA. Usando CPU.
            set "GPU_MODE=cpu"
        )
    )
) else (
    echo   Modo: CPU ^(funcional, mas mais lento^)
)

echo %GPU_MODE%> .gpu_mode

:: ── Step 6: Criar scripts de execução ──
echo.
echo   [6/7] Criando scripts de execucao...

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
echo.
echo :: Detectar Python ^(venv ou portable^)
echo if exist "venv\Scripts\activate.bat" ^(
echo     call venv\Scripts\activate.bat
echo ^) else if exist "python\python.exe" ^(
echo     set "PATH=%%~dp0python;%%~dp0python\Scripts;%%PATH%%"
echo ^)
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
echo echo   Custo: R$ 0,00 ^(IA 100%%%% local^)
echo echo.
echo python main.py
echo pause
) > run.bat

echo   OK Script criado: run.bat

:: ── Step 7: Verificar instalação ──
echo.
echo   [7/7] Verificando instalacao...

if defined USING_EMBEDDED (
    "!PYTHON_CMD!" -c "from llama_cpp import Llama; import flask; import fitz; print('OK')" 2>nul
) else (
    python -c "from llama_cpp import Llama; import flask; import fitz; print('OK')" 2>nul
)
if %errorlevel% equ 0 (
    echo   OK Todos os componentes verificados!
) else (
    echo   AVISO: Alguns componentes podem ter problemas.
)

:: ── Finalização ──
echo.
echo   ╔══════════════════════════════════════════════════╗
echo   ║                                                  ║
echo   ║   Instalacao concluida com sucesso!               ║
echo   ║                                                  ║
echo   ║   Custo: R$ 0,00 — IA 100%% local               ║
echo   ║   Seus dados nunca saem do computador            ║
echo   ║                                                  ║
echo   ╚══════════════════════════════════════════════════╝
echo.
echo   Para iniciar o IPagent:
echo.
echo     run.bat
echo.
echo   Acesse: http://localhost:5000
echo.
echo   Na primeira execucao, o modelo de IA ^(~2 GB^) sera
echo   baixado automaticamente.
echo.

set /p START="  Deseja iniciar o IPagent agora? [S/n] "
if /i not "!START!"=="n" (
    call run.bat
)

endlocal
