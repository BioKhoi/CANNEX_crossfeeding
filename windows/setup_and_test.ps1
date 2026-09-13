[CmdletBinding()]
param(
    [switch]$FullAnalysis
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$ReleaseRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvironmentFile = Join-Path $ReleaseRoot "environment.yml"
$ModelDirectory = Join-Path $ReleaseRoot "models"
$EnvironmentName = "crossfeeding-workflow"
$ModelBaseUrl = "https://www.vmh.life/files/reconstructions/AGORA2/version2.01/sbml_files/individual_reconstructions"

$Models = @(
    [PSCustomObject]@{
        File = "Eubacterium_rectale_ATCC_33656.xml"
        Sha256 = "7672d76c7e9cbd052045375836301470ea15c0a27196a39087604dc8567c2d73"
    },
    [PSCustomObject]@{
        File = "Eubacterium_rectale_DSM_17629.xml"
        Sha256 = "8f447836bfbae3a1add34756c9663e78802f5694a11e7e5ed70bd7d43a9d20e7"
    },
    [PSCustomObject]@{
        File = "Ruminococcus_bicirculans_80_3.xml"
        Sha256 = "23ea1c7d605311640a61aefce3d8f16ecf3570470af391dfcc43a0f0702c0f27"
    },
    [PSCustomObject]@{
        File = "Ruminococcus_bicirculans_ERR1022350.xml"
        Sha256 = "27e1b05b5d34deb5758dab23e2b4b26fd7636fa8cc6513c933ce9e77c6b3751a"
    },
    [PSCustomObject]@{
        File = "Ruminococcus_bromii_ATCC_27255.xml"
        Sha256 = "338a28e9613124af2d8cd577c4c4aaa80e6b0dc2370966bf00c670487c374e86"
    }
)

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

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Ensure-Model {
    param([Parameter(Mandatory = $true)]$Model)

    $Destination = Join-Path $ModelDirectory $Model.File
    if (Test-Path -LiteralPath $Destination -PathType Leaf) {
        $ExistingHash = Get-Sha256 $Destination
        if ($ExistingHash -eq $Model.Sha256) {
            Write-Host "Verified existing model: $($Model.File)" -ForegroundColor Green
            return
        }
        throw "Existing model has the wrong checksum: $Destination. Move it elsewhere and rerun."
    }

    $TemporaryDownload = "$Destination.download"
    $Uri = "$ModelBaseUrl/$($Model.File)"
    Write-Host "Downloading official AGORA2 model: $($Model.File)"
    try {
        Invoke-WebRequest -Uri $Uri -OutFile $TemporaryDownload -UseBasicParsing
        $DownloadedHash = Get-Sha256 $TemporaryDownload
        if ($DownloadedHash -ne $Model.Sha256) {
            throw "Checksum mismatch after downloading $($Model.File)."
        }
        Move-Item -LiteralPath $TemporaryDownload -Destination $Destination
        Write-Host "Verified downloaded model: $($Model.File)" -ForegroundColor Green
    }
    catch {
        if (Test-Path -LiteralPath $TemporaryDownload -PathType Leaf) {
            Remove-Item -LiteralPath $TemporaryDownload -Force
        }
        throw
    }
}

Write-Host "Cross-feeding Windows setup and test" -ForegroundColor Cyan
Write-Host "Release folder: $ReleaseRoot"

$script:CondaCommand = Find-Conda
Write-Host "Conda command: $script:CondaCommand"

New-Item -ItemType Directory -Path $ModelDirectory -Force | Out-Null
foreach ($Model in $Models) {
    Ensure-Model $Model
}

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

    Write-Host "Validating model files, checksums, targets, diet, and dependencies..."
    Invoke-CondaChecked @(
        "run", "-n", $EnvironmentName,
        "python", "find_crossfeeding.py",
        "--gem-dir", "models",
        "--check-only"
    )

    Write-Host "Running synthetic and release tests..."
    Invoke-CondaChecked @(
        "run", "-n", $EnvironmentName,
        "python", "-m", "unittest", "discover", "-s", "tests", "-v"
    )

    if ($FullAnalysis) {
        $OutputDirectory = Join-Path $ReleaseRoot "outputs"
        New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
        $WorkbookOutput = Join-Path $OutputDirectory "windows_test_results.xlsx"
        $JsonOutput = [IO.Path]::ChangeExtension($WorkbookOutput, ".json")

        Write-Host "Running the complete six-stage analysis..." -ForegroundColor Cyan
        Invoke-CondaChecked @(
            "run", "-n", $EnvironmentName,
            "python", "find_crossfeeding.py",
            "--gem-dir", "models",
            "--output", $WorkbookOutput
        )

        $PreviousRegressionPath = $env:CROSSFEEDING_RESULT_JSON
        try {
            $env:CROSSFEEDING_RESULT_JSON = $JsonOutput
            Write-Host "Checking the exact ten retained manuscript edges..."
            Invoke-CondaChecked @(
                "run", "-n", $EnvironmentName,
                "python", "-m", "unittest", "discover", "-s", "tests", "-v"
            )
        }
        finally {
            $env:CROSSFEEDING_RESULT_JSON = $PreviousRegressionPath
        }

        Write-Host "Full analysis output: $WorkbookOutput" -ForegroundColor Green
    }
    else {
        Write-Host "No Excel or JSON result was written. Use -FullAnalysis to run it explicitly."
    }
}
finally {
    Pop-Location
}

Write-Host "All requested Windows checks passed." -ForegroundColor Green
