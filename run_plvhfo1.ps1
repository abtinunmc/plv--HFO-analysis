$pythonPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "python"
)
$py = $null
foreach ($p in $pythonPaths) {
    if (Test-Path $p) { $py = $p; break }
}
if (-not $py) {
    try { $py = (Get-Command python -ErrorAction Stop).Source } catch { }
}
if (-not $py) {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}
Write-Host "Using Python: $py"
& $py "C:\Users\aakhtari\Documents\MATLAB\plvhfo1.py"
