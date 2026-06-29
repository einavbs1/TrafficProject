$trainPid = 56280
Write-Host "Waiting for training process $trainPid to finish..."
while (Get-Process -Id $trainPid -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 30
}
Write-Host "Training done. Starting evaluation..."
Set-Location $PSScriptRoot
python evaluate_V6.py --seeds 5 2>&1 | Tee-Object -FilePath "evaluate_V6_log.txt"
Write-Host "Evaluation complete."
