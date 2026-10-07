# Converts resumes\*.docx to PDF using Microsoft Word (keeps text selectable for ATS).
#   powershell -ExecutionPolicy Bypass -File scripts\docx_to_pdf.ps1 [name-filter]
param([string]$Filter = "*")
$ErrorActionPreference = "Stop"
$dir = Join-Path (Split-Path -Parent $PSScriptRoot) "resumes"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    Get-ChildItem $dir -Recurse -Filter "$Filter.docx" | ForEach-Object {
        $pdf = [IO.Path]::ChangeExtension($_.FullName, ".pdf")
        $doc = $word.Documents.Open($_.FullName, $false, $true)
        $doc.SaveAs([ref]$pdf, [ref]17)   # 17 = wdFormatPDF
        $pages = $doc.ComputeStatistics(2) # 2 = wdStatisticPages
        $doc.Close([ref]0)
        Write-Output "$($_.Name) -> PDF ($pages page(s))"
    }
} finally { $word.Quit() }
