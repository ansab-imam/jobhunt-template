# Runs generate_tasks.py, then shows a Windows toast with today's tasks.
# Clicking the toast opens the dashboard (starting a local web server if needed).
# Built-in Windows APIs only. Falls back to a message box if toasts are unavailable.
#
#   powershell -ExecutionPolicy Bypass -File scripts\notify.ps1
param([int]$Port = 8000)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Url  = "http://localhost:$Port/dashboard/"

function Find-Python {
    foreach ($name in @("python", "py")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notlike "*WindowsApps*") { return $cmd.Source }
    }
    $guess = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue |
             Sort-Object FullName -Descending | Select-Object -First 1
    if ($guess) { return $guess.FullName }
    throw "Python not found. Install it with: winget install -e --id Python.Python.3.12"
}

$Python = Find-Python

# 1. Refresh tasks and get the one-line summary
Push-Location $Root
try { $Summary = (& $Python "scripts\generate_tasks.py" --summary | Select-Object -Last 1) }
finally { Pop-Location }
if (-not $Summary) { $Summary = "Job search: open the dashboard to see today's tasks" }

# 2. Make sure the dashboard server is running (hidden window)
$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    Start-Process -FilePath $Python -ArgumentList "-m", "http.server", "$Port", "--bind", "127.0.0.1" `
        -WorkingDirectory $Root -WindowStyle Hidden
}

# 3. Toast (click opens the dashboard), or a message box as fallback
function Escape-Xml([string]$s) { [System.Security.SecurityElement]::Escape($s) }
try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
    $xml = @"
<toast activationType="protocol" launch="$(Escape-Xml $Url)" scenario="reminder">
  <visual><binding template="ToastGeneric">
    <text>Job search tracker</text>
    <text>$(Escape-Xml $Summary)</text>
  </binding></visual>
  <actions>
    <action content="Open dashboard" activationType="protocol" arguments="$(Escape-Xml $Url)"/>
    <action content="Later" activationType="system" arguments="dismiss"/>
  </actions>
</toast>
"@
    $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
    $doc.LoadXml($xml)
    # Built-in PowerShell app id, so no app registration is needed
    $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show(
        [Windows.UI.Notifications.ToastNotification]::new($doc))
}
catch {
    Add-Type -AssemblyName System.Windows.Forms
    $answer = [System.Windows.Forms.MessageBox]::Show("$Summary`n`nOpen the dashboard now?",
        "Job search tracker", "YesNo", "Information")
    if ($answer -eq "Yes") { Start-Process $Url }
}
Write-Output $Summary
