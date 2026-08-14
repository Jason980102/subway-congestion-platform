param(
    [string]$TaskName = "SubwayCongestionPart4Pipeline",
    [string]$DailyAt = "02:00"
)

$ErrorActionPreference = "Stop"
$Part4Directory = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = (Get-Command py -ErrorAction Stop).Source
$Arguments = "-3.11 `"$Part4Directory\run_pipeline.py`""
$Time = [datetime]::ParseExact($DailyAt, "HH:mm", $null)

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument $Arguments `
    -WorkingDirectory $Part4Directory
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Change-aware Subway Part IV ETL and candidate retraining pipeline" `
    -Force | Out-Null

Write-Host "Scheduled task '$TaskName' installed for $DailyAt daily."
