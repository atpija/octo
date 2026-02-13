# Stop script on any error
$ErrorActionPreference = "Stop"

$BaseUrl = "https://www.project-octo.com/download"

Write-Host "Fetching latest Octo version..."

# --- Get latest version ---
$Version = Invoke-WebRequest "$BaseUrl/latest.txt" -UseBasicParsing | Select-Object -ExpandProperty Content
$Version = $Version.Trim()

if (-not $Version) {
    Write-Error "Could not determine latest version."
    exit 1
}

Write-Host "Latest version detected: $Version"

# --- Build filenames ---
$Installer = "octo-runner-setup-$Version.exe"
$DownloadUrl = "$BaseUrl/v$Version/$Installer"
$HashUrl = "$DownloadUrl.sha256"

Write-Host "Downloading installer..."
Invoke-WebRequest $DownloadUrl -OutFile $Installer

Write-Host "Downloading SHA256 hash..."
Invoke-WebRequest $HashUrl -OutFile "$Installer.sha256"

# --- Verify SHA256 ---
Write-Host "Verifying integrity..."

$ExpectedHash = (Get-Content "$Installer.sha256").Split(" ")[0].ToLower()
$ActualHash = (Get-FileHash $Installer -Algorithm SHA256).Hash.ToLower()

if ($ActualHash -ne $ExpectedHash) {
    Write-Error "SHA256 verification failed! Installation aborted."
    Remove-Item $Installer -ErrorAction SilentlyContinue
    Remove-Item "$Installer.sha256" -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "Integrity check passed."

# --- Silent install (NSIS uses /S) ---
Write-Host "Installing Octo Runner v$Version..."
Start-Process ".\$Installer" -ArgumentList "/S" -Wait

# --- Cleanup ---
Remove-Item $Installer -ErrorAction SilentlyContinue
Remove-Item "$Installer.sha256" -ErrorAction SilentlyContinue

Write-Host "Octo Runner v$Version installed successfully."
