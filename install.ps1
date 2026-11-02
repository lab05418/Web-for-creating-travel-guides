[CmdletBinding()]
param(
    [switch]$Rebuild
)

# 原生命令（pip/npm/node）经常向 stderr 写警告；这里不用 Stop，
# 统一通过 $LASTEXITCODE 判断成功与否，避免把 npm 的普通警告当成致命错误。
$ErrorActionPreference = 'Continue'
$Root = $PSScriptRoot
Set-Location -LiteralPath $Root

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "  [!] $Message" -ForegroundColor Yellow
}

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "安装失败：$Message" -ForegroundColor Red
    Write-Host "请把上面的错误信息截图或复制给维护者。" -ForegroundColor Red
    exit 1
}

function Read-Yes([string]$Prompt) {
    try {
        $answer = Read-Host $Prompt
        if ([string]::IsNullOrWhiteSpace($answer)) { return $true }
        return $answer -match '^[Yy]'
    } catch {
        return $false
    }
}

function Test-PythonVersion([string]$Executable, [string[]]$Arguments) {
    try {
        $output = & $Executable @Arguments 2>&1
        if ($LASTEXITCODE -eq 0 -and (($output -join "`n") -match 'Python\s+3\.10')) {
            return $true
        }
    } catch { }
    return $false
}

function Find-Python310 {
    $candidates = @()
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $candidates += [pscustomobject]@{ Executable = $py.Source; Prefix = @('-3.10') }
    }
    $knownPaths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe'),
        'C:\Program Files\Python310\python.exe',
        'C:\Python310\python.exe'
    )
    foreach ($path in $knownPaths) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            $candidates += [pscustomobject]@{ Executable = $path; Prefix = @() }
        }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $candidates += [pscustomobject]@{ Executable = $python.Source; Prefix = @() }
    }
    foreach ($candidate in $candidates) {
        $versionArgs = @($candidate.Prefix) + @('-V')
        if (Test-PythonVersion -Executable $candidate.Executable -Arguments $versionArgs) {
            return $candidate
        }
    }
    return $null
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:PATH = (@($machine, $user, $env:PATH) | Where-Object { $_ }) -join ';'
}

function Test-NodeDir([string]$Dir) {
    if ([string]::IsNullOrWhiteSpace($Dir)) { return $false }
    try {
        $node = [System.IO.Path]::Combine($Dir, 'node.exe')
        $npm = [System.IO.Path]::Combine($Dir, 'npm.cmd')
        return (Test-Path -LiteralPath $node -PathType Leaf -ErrorAction Stop) -and
               (Test-Path -LiteralPath $npm -PathType Leaf -ErrorAction Stop)
    } catch {
        return $false
    }
}

function Find-Node {
    # 记录文件可能来自另一台机器/另一个盘符（例如项目从 F: 拷贝到 D:）。
    # 必须忽略失效路径，不能让它中断安装。
    $recordFile = Join-Path $Root 'backend\.venv\.farway-node-dir'
    if (Test-Path -LiteralPath $recordFile) {
        try {
            $recorded = ([System.IO.File]::ReadAllText($recordFile, [System.Text.Encoding]::UTF8)).Trim()
            if (Test-NodeDir $recorded) { return $recorded }
        } catch {
            # 忽略损坏/不可访问的旧记录，继续向下查找。
        }
    }

    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($nodeCommand) {
        $dir = Split-Path -Parent $nodeCommand.Source
        if (Test-NodeDir $dir) { return $dir }
    }

    $candidates = @()
    if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles 'nodejs') }
    $programFilesX86 = ${env:ProgramFiles(x86)}
    if ($programFilesX86) { $candidates += (Join-Path $programFilesX86 'nodejs') }
    if ($env:LOCALAPPDATA) { $candidates += (Join-Path $env:LOCALAPPDATA 'Programs\nodejs') }

    foreach ($dir in $candidates) {
        if (Test-NodeDir $dir) { return $dir }
    }

    $tools = Join-Path $Root 'tools'
    if (Test-Path -LiteralPath $tools) {
        $dirs = Get-ChildItem -LiteralPath $tools -Directory -Filter 'node-*' -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending
        foreach ($item in $dirs) {
            if (Test-NodeDir $item.FullName) { return $item.FullName }
        }
    }
    return $null
}

function Get-CombinedHash([string[]]$Paths) {
    $parts = @()
    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            Fail "缺少文件：$path"
        }
        $parts += (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    }
    return ($parts -join '-')
}

Write-Host "Farway 一键安装" -ForegroundColor Magenta
Write-Host "项目目录：$Root" -ForegroundColor DarkGray

# 1. Python 3.10
Write-Step "检查 Python 3.10"
$python = Find-Python310
if (-not $python) {
    Write-Warn "未检测到 Python 3.10。"
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        if (Read-Yes "是否现在用 winget 安装 Python 3.10？(Y/n)") {
            & winget install --id Python.Python.3.10 -e --accept-source-agreements --accept-package-agreements
            Start-Sleep -Seconds 2
            Refresh-Path
            $python = Find-Python310
        }
    }
}
if (-not $python) {
    Fail "未找到 Python 3.10。请先从 https://www.python.org/downloads/ 安装 Python 3.10.x 64 位（勾选 Add python.exe to PATH），然后重新运行本脚本。"
}
$pythonVersionArgs = @($python.Prefix) + @('-V')
$pythonVersion = (& $python.Executable @pythonVersionArgs 2>&1) -join ' '
Write-Ok "Python：$pythonVersion"

# 2. Node.js 与 npm
Write-Step "检查 Node.js 与 npm"
$nodeDir = Find-Node
if (-not $nodeDir) {
    Write-Warn "未检测到 Node.js。"
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        if (Read-Yes "是否现在用 winget 安装 Node.js LTS？(Y/n)") {
            & winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
            Start-Sleep -Seconds 2
            Refresh-Path
            $nodeDir = Find-Node
        }
    }
}
if (-not $nodeDir) {
    Fail "未找到 Node.js/npm。请先从 https://nodejs.org/ 安装 LTS 版本（安装时勾选 Add to PATH），然后重新运行本脚本。"
}
$nodeExe = Join-Path $nodeDir 'node.exe'
$npmCmd = Join-Path $nodeDir 'npm.cmd'
$env:PATH = "$nodeDir;$env:PATH"
$nodeVersion = ((& $nodeExe -v 2>&1) -join ' ').Trim()
if ($nodeVersion -notmatch '^v(\d+)\.') {
    Fail "Node.js 版本信息异常：$nodeVersion"
}
$nodeMajor = [int]$Matches[1]
if ($nodeMajor -lt 18) {
    Fail "Node.js 版本过低（当前 $nodeVersion）。请安装 Node.js 18 或更高版本（推荐 20/22/24 LTS）。"
}
$npmVersion = ((& $npmCmd -v 2>&1) -join ' ').Trim()
Write-Ok "Node.js：$nodeVersion；npm：$npmVersion"

# 3. 虚拟环境
$backend = Join-Path $Root 'backend'
$frontend = Join-Path $Root 'frontend'
$venv = Join-Path $backend '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
Write-Step "准备 Python 虚拟环境"

function New-FarwayVenv {
    Push-Location $backend
    try {
        $createArgs = @($python.Prefix) + @('-m', 'venv', '.venv')
        & $python.Executable @createArgs
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
        Fail "创建虚拟环境失败。请确认 Python 3.10 安装完整后重试。"
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    New-FarwayVenv
} else {
    $venvVersion = ((& $venvPython -V 2>&1) -join ' ').Trim()
    if ($LASTEXITCODE -ne 0 -or $venvVersion -notmatch 'Python\s+3\.10') {
        Write-Warn "现有 backend\.venv 不可用（可能从其他目录复制或已损坏），正在自动重建..."
        try {
            Remove-Item -LiteralPath $venv -Recurse -Force -ErrorAction Stop
        } catch {
            Fail "无法删除损坏的 backend\.venv。请关闭正在占用它的 PowerShell/编辑器窗口后重新运行 install.cmd。"
        }
        New-FarwayVenv
    }
}

$venvVersion = ((& $venvPython -V 2>&1) -join ' ').Trim()
if ($LASTEXITCODE -ne 0 -or $venvVersion -notmatch 'Python\s+3\.10') {
    Fail "虚拟环境仍不可用（$venvVersion）。请确认 Python 3.10 安装完整，或手动删除 backend\.venv 后重试。"
}
$nodeRecordFile = Join-Path $venv '.farway-node-dir'
[System.IO.File]::WriteAllText($nodeRecordFile, $nodeDir, (New-Object System.Text.UTF8Encoding -ArgumentList $false))
Write-Ok "虚拟环境：$venv"

# 4. 后端 Python 依赖
$requirements = Join-Path $backend 'requirements.txt'
if (-not (Test-Path -LiteralPath $requirements)) {
    Fail "缺少 backend\requirements.txt，请确认项目文件完整。"
}
$requirementsHash = (Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
$requirementsMarker = Join-Path $venv '.farway-requirements.sha256'
$needPip = $true
if ((Test-Path -LiteralPath $requirementsMarker) -and
    ((Get-Content -Raw -LiteralPath $requirementsMarker).Trim() -eq $requirementsHash)) {
    & $venvPython -c "import fastapi, uvicorn, dotenv" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $needPip = $false
        Write-Ok "后端 Python 依赖已安装"
    }
}
if ($needPip) {
    Write-Step "安装后端 Python 依赖（首次可能需要几分钟）"
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        Fail "升级 pip 失败。请检查网络，或改用镜像后重试：`"$venvPython`" -m pip install -r `"$requirements`" -i https://pypi.tuna.tsinghua.edu.cn/simple"
    }
    & $venvPython -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) {
        Fail "后端 Python 依赖安装失败。请检查网络；国内网络可改用镜像：`"$venvPython`" -m pip install -r `"$requirements`" -i https://pypi.tuna.tsinghua.edu.cn/simple"
    }
    Set-Content -LiteralPath $requirementsMarker -Value $requirementsHash -Encoding ASCII
    Write-Ok "后端 Python 依赖安装完成"
}

# 5. 后端 Node 依赖
$backendLock = Join-Path $backend 'package-lock.json'
$backendPackage = Join-Path $backend 'package.json'
$backendHash = Get-CombinedHash -Paths @($backendLock, $backendPackage)
$backendMarker = Join-Path $backend 'node_modules\.farway-package-lock.sha256'
$needBackendNpm = $true
if ((Test-Path (Join-Path $backend 'node_modules\crypto-js\package.json')) -and
    (Test-Path -LiteralPath $backendMarker) -and
    ((Get-Content -Raw -LiteralPath $backendMarker).Trim() -eq $backendHash)) {
    $needBackendNpm = $false
    Write-Ok "后端 Node 依赖已安装"
}
if ($needBackendNpm) {
    Write-Step "安装后端 Node 依赖（小红书签名）"
    Push-Location $backend
    try {
        & $npmCmd install --no-audit --no-fund --loglevel=error
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) {
        Fail "后端 Node 依赖安装失败。请检查网络后重试。"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backendMarker) | Out-Null
    Set-Content -LiteralPath $backendMarker -Value $backendHash -Encoding ASCII
    Write-Ok "后端 Node 依赖安装完成"
}

# 6. 前端依赖
$frontendLock = Join-Path $frontend 'package-lock.json'
$frontendPackage = Join-Path $frontend 'package.json'
$frontendHash = Get-CombinedHash -Paths @($frontendLock, $frontendPackage)
$frontendMarker = Join-Path $frontend 'node_modules\.farway-package-lock.sha256'
$needFrontendNpm = $true
if ((Test-Path (Join-Path $frontend 'node_modules\vite\package.json')) -and
    (Test-Path -LiteralPath $frontendMarker) -and
    ((Get-Content -Raw -LiteralPath $frontendMarker).Trim() -eq $frontendHash)) {
    $needFrontendNpm = $false
    Write-Ok "前端依赖已安装"
}
if ($needFrontendNpm) {
    Write-Step "安装前端依赖（首次可能需要几分钟）"
    Push-Location $frontend
    try {
        & $npmCmd ci --no-audit --no-fund --loglevel=error
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "npm ci 失败，改用 npm install 重试..."
            & $npmCmd install --no-audit --no-fund --loglevel=error
        }
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $frontend 'node_modules\vite\package.json'))) {
        Fail "前端依赖安装失败。请检查网络，或在 frontend 目录执行 npm config set registry https://registry.npmmirror.com 后重试。"
    }
    Set-Content -LiteralPath $frontendMarker -Value $frontendHash -Encoding ASCII
    Write-Ok "前端依赖安装完成"
}

# 7. 构建前端
$distIndex = Join-Path $frontend 'dist\index.html'
$needBuild = $Rebuild -or -not (Test-Path -LiteralPath $distIndex)
if ($needBuild) {
    Write-Step "构建前端页面（首次可能需要几分钟）"
    Push-Location $frontend
    try {
        $env:VITE_API_BASE_URL = ''
        Remove-Item Env:VITE_AMAP_WEB_JS_KEY -ErrorAction SilentlyContinue
        Remove-Item Env:VITE_AMAP_SECURITY_JS_CODE -ErrorAction SilentlyContinue
        & $npmCmd run build
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $distIndex)) {
        Fail "前端构建失败。请查看上方错误；常见原因是 Node.js 版本过低或网络问题。"
    }
    Write-Ok "前端构建完成：frontend\dist"
} else {
    Write-Ok "前端页面已构建（如需强制重建，运行 install.ps1 -Rebuild）"
}

# 8. 默认配置与数据目录
$envFile = Join-Path $backend '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Step "生成后端默认配置"
    $envContent = @"
# Farway 本地默认配置
# 请优先在网页右上角「设置」中填写 API Key；无需手动编辑此文件。
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
"@
    $utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false
    [System.IO.File]::WriteAllText($envFile, $envContent, $utf8)
    Write-Ok "已生成 backend\.env（不含任何密钥）"
} else {
    Write-Ok "保留现有 backend\.env"
}
New-Item -ItemType Directory -Force -Path (Join-Path $backend 'data') | Out-Null

Write-Host ""
Write-Host "安装完成！" -ForegroundColor Green
Write-Host "下一步：双击 start.cmd（或在 PowerShell 中运行 .\start.ps1）" -ForegroundColor White
Write-Host "首次打开网页后，点击右上角齿轮，填写 LLM API Key、高德 Key 等并保存。" -ForegroundColor White
Write-Host ""
