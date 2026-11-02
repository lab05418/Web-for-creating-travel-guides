[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Continue'
$Root = $PSScriptRoot
Set-Location -LiteralPath $Root

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

function Write-Ok([string]$Message) {
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "  [!] $Message" -ForegroundColor Yellow
}

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "启动失败：$Message" -ForegroundColor Red
    Write-Host "如果无法解决，请重新运行 install.cmd 修复安装。" -ForegroundColor Red
    exit 1
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
    # 必须忽略失效路径，不能让它中断启动。
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

function Test-FarwayHealth([int]$TargetPort) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:$TargetPort/health" -TimeoutSec 2 -ErrorAction Stop
        return ($response.status -eq 'healthy')
    } catch {
        return $false
    }
}

function Open-FarwayPage([int]$TargetPort) {
    try {
        Start-Process "http://127.0.0.1:$TargetPort" | Out-Null
    } catch {
        Write-Warn "无法自动打开浏览器，请手动访问 http://127.0.0.1:$TargetPort"
    }
}

$backend = Join-Path $Root 'backend'
$frontend = Join-Path $Root 'frontend'
$venvScripts = Join-Path $backend '.venv\Scripts'
$venvPython = Join-Path $venvScripts 'python.exe'
$uvxExe = Join-Path $venvScripts 'uvx.exe'

Write-Host "Farway 一键启动" -ForegroundColor Magenta
Write-Host "项目目录：$Root" -ForegroundColor DarkGray

# 1. 检查安装结果
if (-not (Test-Path -LiteralPath $venvPython)) {
    Fail "尚未安装。请先双击 install.cmd（或运行 .\install.ps1）。"
}
$venvVersion = ((& $venvPython -V 2>&1) -join ' ').Trim()
if ($LASTEXITCODE -ne 0 -or $venvVersion -notmatch 'Python\s+3\.10') {
    Fail "Python 虚拟环境不可用（可能从其他目录复制或已损坏）。请运行 install.cmd，它会自动重建虚拟环境。"
}
if (-not (Test-Path -LiteralPath (Join-Path $frontend 'dist\index.html'))) {
    Fail "前端页面尚未构建。请先双击 install.cmd（或运行 .\install.ps1）。"
}
if (-not (Test-Path -LiteralPath (Join-Path $backend 'node_modules\crypto-js\package.json'))) {
    Fail "后端 Node 依赖不完整。请先双击 install.cmd（或运行 .\install.ps1）。"
}
if (-not (Test-Path -LiteralPath $uvxExe)) {
    Fail "Python 依赖不完整（缺少 uvx）。请重新运行 install.cmd。"
}

$nodeDir = Find-Node
if (-not $nodeDir) {
    Fail "未找到 Node.js。请先安装 Node.js 18+（推荐 20/22/24 LTS），或重新运行 install.cmd。"
}

$env:PATH = "$nodeDir;$venvScripts;$env:PATH"
$nodeVersion = ((& (Join-Path $nodeDir 'node.exe') -v 2>&1) -join ' ').Trim()
Write-Ok "Node.js：$nodeVersion"

# 2. 如果已经在运行，直接打开页面
if (Test-FarwayHealth -TargetPort $Port) {
    Write-Ok "Farway 已经在 http://127.0.0.1:$Port 运行"
    if (-not $NoBrowser) { Open-FarwayPage -TargetPort $Port }
    exit 0
}

# 3. 端口检查
try {
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
} catch {
    $listeners = $null
}
if ($listeners) {
    $connection = @($listeners)[0]
    $ownerPid = $connection.OwningProcess
    $ownerName = ''
    try {
        $ownerName = (Get-Process -Id $ownerPid -ErrorAction SilentlyContinue).ProcessName
    } catch { }
    $ownerText = if ($ownerName) { "$ownerName (PID $ownerPid)" } else { "PID $ownerPid" }
    Fail "端口 $Port 已被其他程序占用：$ownerText。请关闭该程序，或用 .\start.ps1 -Port 8001 换一个端口。"
}

# 4. 启动后端（新窗口，关闭该窗口即停止）
Write-Host ""
Write-Host "==> 启动后端，请稍候..." -ForegroundColor Cyan
$backendCommand = '& "' + $venvPython + '" -m uvicorn app.api.main:app --host 127.0.0.1 --port ' + $Port
try {
    $process = Start-Process -FilePath 'powershell.exe' `
        -ArgumentList @('-NoProfile', '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $backendCommand) `
        -WorkingDirectory $backend -WindowStyle Normal -PassThru
} catch {
    Fail "无法启动后端进程：$($_.Exception.Message)"
}
if (-not $process) {
    Fail "无法启动后端进程。"
}

$deadline = (Get-Date).AddSeconds(90)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    if (Test-FarwayHealth -TargetPort $Port) {
        $healthy = $true
        break
    }
    try {
        $process.Refresh()
    } catch { }
    if ($process.HasExited) {
        Fail "后端进程已退出（退出码 $($process.ExitCode)）。请查看新打开的后端命令行窗口中的错误信息，修复后重新运行 start.cmd。"
    }
    Start-Sleep -Milliseconds 600
}

if (-not $healthy) {
    Fail "后端已启动，但 90 秒内未通过健康检查。请查看新打开的后端命令行窗口中的错误信息；常见原因是依赖未安装完整、端口冲突或配置错误。"
}

Write-Ok "Farway 已启动：http://127.0.0.1:$Port"
if (-not $NoBrowser) { Open-FarwayPage -TargetPort $Port }
Write-Host ""
Write-Host "关闭新打开的后端命令行窗口即可停止 Farway。" -ForegroundColor White
Write-Host "首次使用：点击网页右上角齿轮，填写 LLM API Key、高德 Key 等并保存。" -ForegroundColor White
