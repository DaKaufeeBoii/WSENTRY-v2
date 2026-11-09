# Run on laptop A from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\unoq\push_to_board.ps1 -Board <BOARD_IP>
param([Parameter(Mandatory = $true)][string]$Board)
Set-Location (Join-Path $PSScriptRoot "..\..")
$crlf = Get-ChildItem scripts\unoq\*.sh | Where-Object { (Get-Content -Raw $_.FullName) -match "`r" }
if ($crlf) { throw "CRLF line endings in: $($crlf.Name -join ', '). Convert them to LF first." }
$files = @(
  "scripts/detector_server.py", "scripts/check_parity.py",
  "scripts/attack_samples.json", "scripts/golden_predictions.json", "scripts/unoq",
  "src/__init__.py", "src/utils.py", "src/live/__init__.py", "src/live/inference.py",
  "src/models/__init__.py", "src/models/hybrid_dl.py", "src/models/calibration.py",
  "models/saved/hybrid_model.pt", "models/saved/temp_scaler.pt",
  "models/saved/model_config.json", "models/saved/scaler.pkl", "models/saved/scaler.json",
  "src/features/__init__.py", "src/features/ciciot_features.py",
  "src/data/__init__.py", "src/data/dataset_loader.py", "src/live/cic_live.py"
)
tar -czf wsentry-unoq.tgz @files
if ($LASTEXITCODE) { throw "tar failed (is scripts/golden_predictions.json there? run P1.4)" }
scp wsentry-unoq.tgz "arduino@${Board}:~/"
if ($LASTEXITCODE) { throw "scp failed: check the board IP and that SSH works (P2.4)" }
ssh "arduino@$Board" "mkdir -p ~/w-sentry && tar -xzf ~/wsentry-unoq.tgz -C ~/w-sentry && rm ~/wsentry-unoq.tgz && ls ~/w-sentry"
if ($LASTEXITCODE) { throw "remote unpack failed" }
Remove-Item wsentry-unoq.tgz
Write-Host "pushed to arduino@${Board}:~/w-sentry"
