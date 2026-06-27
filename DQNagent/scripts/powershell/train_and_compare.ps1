# FlowGrid: train + compare from PowerShell (live lines in this window).
# Usage:
#   .\scripts\powershell\train_and_compare.ps1 -Fresh
#   .\scripts\powershell\train_and_compare.ps1 -Resume
#   .\scripts\powershell\train_and_compare.ps1 -Curriculum -Fresh

param(
    [switch]$Fresh,
    [switch]$Resume,
    [switch]$Curriculum,
    [int]$Episodes = 500,
    [int]$MaxCycles = 10,
    [int]$CheckpointEvery = 10,
    [string]$Map = "flowgrid",
    [int]$CompareSeed = 42,
    [double]$InjectSeconds = 800
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)

$py = "python"
if ($Curriculum) {
    $args = @(
        "scripts/run_curriculum.py",
        "--map", $Map,
        "--episodes-per-cycle", "$Episodes",
        "--max-cycles", "$MaxCycles",
        "--checkpoint-every", "$CheckpointEvery",
        "--compare-seed", "$CompareSeed",
        "--inject-seconds", "$InjectSeconds"
    )
    if ($Fresh) { $args += "--fresh" }
    & $py @args
    exit $LASTEXITCODE
}

$args = @(
    "scripts/run_train_then_compare.py",
    "--map", $Map,
    "--episodes", "$Episodes",
    "--checkpoint-every", "$CheckpointEvery",
    "--compare-seed", "$CompareSeed",
    "--inject-seconds", "$InjectSeconds"
)
if ($Fresh) { $args += "--fresh" }
if ($Resume) { $args += "--resume" }
& $py @args
exit $LASTEXITCODE
