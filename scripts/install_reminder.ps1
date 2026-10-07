# Registers scripts\notify.ps1 as a daily Windows Task Scheduler job.
#
#   powershell -ExecutionPolicy Bypass -File scripts\install_reminder.ps1              # 10:00 daily
#   powershell -ExecutionPolicy Bypass -File scripts\install_reminder.ps1 -Time 18:30  # another time
#   powershell -ExecutionPolicy Bypass -File scripts\install_reminder.ps1 -Remove      # uninstall
param(
    [string]$Time = "10:00",
    [string]$TaskName = "JobSearchTracker-DailyReminder",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Removed scheduled task '$TaskName' (if it existed)."
    return
}

$Notify = Join-Path $PSScriptRoot "notify.ps1"
$Root   = Split-Path -Parent $PSScriptRoot
$At     = [datetime]::ParseExact($Time, "HH:mm", $null)

$action   = New-ScheduledTaskAction -Execute "powershell.exe" `
              -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Notify`"" `
              -WorkingDirectory $Root
$trigger  = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
              -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Daily job search reminder (job tracker repo: $Root)" -Force | Out-Null

Write-Output "Installed '$TaskName': runs daily at $Time (runs late if the PC was off)."
Write-Output "Test it now:  Start-ScheduledTask -TaskName $TaskName"
Write-Output "Remove it:    powershell -ExecutionPolicy Bypass -File scripts\install_reminder.ps1 -Remove"
