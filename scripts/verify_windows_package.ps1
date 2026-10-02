param(
    [Parameter(Mandatory = $true)][string]$PackageDirectory,
    [Parameter(Mandatory = $true)][string]$Video,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [ValidateSet('pipeline', 'reader', 'smoke')][string]$Mode = 'pipeline',
    [int]$MaxFrames = 0,
    [switch]$Cpu
)

$ErrorActionPreference = 'Stop'
$packagePath = (Resolve-Path -LiteralPath $PackageDirectory).Path
$videoPath = (Resolve-Path -LiteralPath $Video).Path
$executablePath = Join-Path $packagePath 'FaceBlur Studio.exe'
if (-not (Test-Path -LiteralPath $executablePath -PathType Leaf)) {
    throw "Packaged application not found: $executablePath"
}
if (Test-Path -LiteralPath $OutputDirectory) {
    throw 'Use a new output directory to preserve earlier verification results.'
}
$outputPath = (New-Item -ItemType Directory -Path $OutputDirectory).FullName
$resultPath = Join-Path $outputPath 'report.json'
$taskArguments = switch ($Mode) {
    'pipeline' { @('--verify-pipeline', $videoPath, $outputPath) }
    'reader' { @('--verify-reader', $videoPath, $resultPath) }
    'smoke' { @('--smoke-test', $videoPath, $resultPath) }
}
if ($MaxFrames -gt 0 -and $Mode -ne 'reader') {
    $taskArguments += [string]$MaxFrames
}

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $executablePath
$startInfo.Arguments = ($taskArguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
$startInfo.WorkingDirectory = $outputPath
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$startInfo.EnvironmentVariables['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"
foreach ($name in @('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'FACEBLUR_DEVICE', 'FACEBLUR_DML_DEVICE')) {
    $startInfo.EnvironmentVariables.Remove($name)
}
if ($Cpu) { $startInfo.EnvironmentVariables['FACEBLUR_DEVICE'] = 'cpu' }

$process = [System.Diagnostics.Process]::Start($startInfo)
Write-Output "Verification started: PID=$($process.Id), mode=$Mode"
$process.WaitForExit()
if ($process.ExitCode -ne 0) {
    throw "Application exited with code $($process.ExitCode). See $resultPath and the application log."
}
if (-not (Test-Path -LiteralPath $resultPath)) { throw 'Application did not produce a report.' }
$result = Get-Content -LiteralPath $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Mode -ne 'smoke' -and $result.status -ne 'passed') {
    throw "Verification did not pass. See $resultPath"
}
Write-Output "Verification passed: $resultPath"
