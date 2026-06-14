# ACAS Pro - 数据库备份脚本（PowerShell）
# 用途: 备份 ACAS Pro SQLite 数据库
# 用法: .\backup.ps1
# 支持: Windows 任务计划程序 + Docker 容器
# ============================================
param(
    [int]$KeepDays = 7
)
$ErrorActionPreference = "Stop"
# ============================================
# 配置
# ============================================
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = $PSScriptRoot }
$DataDir = Join-Path $ProjectRoot "data"
$BackupDir = Join-Path $ProjectRoot "backups"
$DBPath = Join-Path $DataDir "acas..db"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DateTag = Get-Date -Format "yyyyMMdd"
$BackupFile = "acas_${Timestamp}.db"
# ============================================
# 初始化
# ============================================
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}
Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] === ACAS Pro 数据库备份 ===" -ForegroundColor Cyan
# ============================================
# 备份函数
# ============================================
function Invoke-ACASBackup {
    param([string]$BackupPath)
    $startTime = Get-Date
    Write-Host "开始备份: $DBPath -> $BackupPath" -ForegroundColor Yellow

    # 复制数据库文件（SQLite WAL 模式下需要两个文件）
    Copy-Item -Path $DBPath -Destination $BackupPath -Force -ErrorAction Stop
    # 同时复制 WAL 文件（如果存在）
    $walPath = "${DBPath}-wal"
    if (Test-Path $walPath) {
        Copy-Item -Path $walPath -Destination "${BackupPath}-wal" -Force
    }

    $duration = ((Get-Date) - $startTime).TotalSeconds
    $size = (Get-Item $BackupPath).Length
    $sizeMB = [math]::Round($size / 1MB, 2)
    Write-Host "✅ 备份完成: $BackupPath ($sizeMB MB, ${duration}s)" -ForegroundColor Green
}
# ============================================
# 清理函数
# ============================================
function Remove-OldBackups {
    param([int]$Days)
    Write-Host "清理超过 $Days 天的备份..." -ForegroundColor Yellow

    $cutoff = (Get-Date).AddDays(-$Days)
    $oldBackups = Get-ChildItem -Path $BackupDir -Filter "acas_*.db" |
        Where-Object { $_.LastWriteTime -lt $cutoff }

    foreach ($f in $oldBackups) {
        Write-Host "删除: $($f.Name)" -ForegroundColor DarkGray
        Remove-Item $f.FullName -Force -ErrorAction SilentlyContinue
        $walFile = "${BackupDir}\${$f.BaseName}.db-wal"
        if (Test-Path $walFile) {
            Remove-Item $walFile -Force -ErrorAction SilentlyContinue
        }
    }

    $remaining = (Get-ChildItem -Path $BackupDir -Filter "acas_*.db" | Measure-Object).Count
    Write-Host "清理完成，剩余 $remaining 个备份" -ForegroundColor Gray
}
# ============================================
# 主流程
# ============================================
# 检查数据库文件
if (-not (Test-Path $DBPath)) {
    Write-Host "❌ 数据库文件不存在: $DBPath" -ForegroundColor Red
    exit 1
}
# 创建备份
$BackupPath = Join-Path $BackupDir $BackupFile
Invoke-ACASBackup -BackupPath $BackupPath
# 清理旧备份
Remove-OldBackups -Days $KeepDays
# 校验和
$hashPath = "${BackupPath}.sha256"
$hash = Get-FileHash -Path $BackupPath -Algorithm SHA256
$hashContent = "$($hash.Hash)  $BackupFile"
$hashContent | Out-File -FilePath $hashPath -Encoding ASCII -NoNewline
Write-Host "校验和: $hashPath" -ForegroundColor Gray
Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] === 备份完成 ===" -ForegroundColor Cyan