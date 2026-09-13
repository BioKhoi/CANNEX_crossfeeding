[CmdletBinding()]
param(
    [switch]$FullAnalysis
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$ReleaseRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvironmentFile = Join-Path $ReleaseRoot "environment.yml"
$EnvironmentName = "crossfeeding-workflow"
$ValidationCaseDirectory = Join-Path $ReleaseRoot "validation\cases\01_two_donors_control"
$ModelDirectory = Join-Path $ValidationCaseDirectory "models"
$TargetFile = Join-Path $ValidationCaseDirectory "config\targets.tsv"

function Find-Conda {
    if (Get-Command conda -ErrorAction SilentlyContinue) {
        return "conda"
    }

    $Candidates = @(
        (Join-Path $env:USERPROFILE "miniconda3\Scripts\conda.exe"),
        (Join-Path $env:USERPROFILE "anaconda3\Scripts\conda.exe"),
        "C:\ProgramData\miniconda3\Scripts\conda.exe",
        "C:\ProgramData\anaconda3\Scripts\conda.exe"
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            return $Candidate
        }
    }

    throw "Conda was not found. Install 64-bit Miniconda or Anaconda, then run this file again."
}

function Invoke-CondaChecked {
    param([Parameter(Mandatory = $true)][string[]]$CondaArguments)

    & $script:CondaCommand @CondaArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Conda command failed: conda $($CondaArguments -join ' ')"
    }
}

Write-Host "Cross-feeding Windows setup and test" -ForegroundColor Cyan
Write-Host "Release folder: $ReleaseRoot"
Write-Host "Bundled tutorial: Validation Case 01"

$script:CondaCommand = Find-Conda
Write-Host "Conda command: $script:CondaCommand"

$EnvironmentJson = & $script:CondaCommand env list --json
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list Conda environments."
}
$EnvironmentPaths = ($EnvironmentJson | ConvertFrom-Json).envs
$EnvironmentExists = @(
    $EnvironmentPaths | Where-Object { (Split-Path $_ -Leaf) -eq $EnvironmentName }
).Count -gt 0

if (-not $EnvironmentExists) {
    Write-Host "Creating the pinned Conda environment. This may take several minutes."
    Invoke-CondaChecked @("env", "create", "--file", $EnvironmentFile)
}
else {
    Write-Host "Using existing Conda environment: $EnvironmentName"
}

Push-Location $ReleaseRoot
try {
    Write-Host "Checking Python and scientific dependencies..."
    Invoke-CondaChecked @("run", "-n", $EnvironmentName, "python", "--version")
    Invoke-CondaChecked @("run", "-n", $EnvironmentName, "mene", "--version")
    Invoke-CondaChecked @("run", "-n", $EnvironmentName, "clingo", "--version")

    Write-Host "Validating the bundled Case 01 models, manifest, targets, diet, and dependencies..."
    Invoke-CondaChecked @(
        "run", "-n", $EnvironmentName,
        "python", "find_crossfeeding.py",
        "--gem-dir", $ModelDirectory,
        "--targets", $TargetFile,
        "--check-only"
    )

    Write-Host "Running synthetic and release tests..."
    Invoke-CondaChecked @(
        "run", "-n", $EnvironmentName,
        "python", "-m", "unittest", "discover", "-s", "tests", "-v"
    )

    Write-Host "Checking the seven locked validation comparisons..."
    Invoke-CondaChecked @(
        "run", "-n", $EnvironmentName,
        "python", "validate_expected_cases.py"
    )

    if ($FullAnalysis) {
        $OutputDirectory = Join-Path $ReleaseRoot "outputs"
        New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
        $WorkbookOutput = Join-Path $OutputDirectory "case01_windows_test.xlsx"

        Write-Host "Running the complete six-stage Case 01 tutorial..." -ForegroundColor Cyan
        Invoke-CondaChecked @(
            "run", "-n", $EnvironmentName,
            "python", "find_crossfeeding.py",
            "--gem-dir", $ModelDirectory,
            "--targets", $TargetFile,
            "--output", $WorkbookOutput
        )

        Write-Host "Case 01 Excel output: $WorkbookOutput" -ForegroundColor Green
    }
    else {
        Write-Host "No new Excel or JSON result was written. Use -FullAnalysis to run Case 01 explicitly."
    }
}
finally {
    Pop-Location
}

Write-Host "All requested Windows checks passed." -ForegroundColor Green
