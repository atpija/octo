$Version = "0.2.0"
$BaseUrl = "https://www.project-octo.com/download/v$Version"

Write-Host "Installing Octo Runner v$Version..."

$Installer = "octo-runner-$Version-setup.exe"

# Datei herunterladen
Invoke-WebRequest "$BaseUrl/$Installer" -OutFile $Installer

# Silent Installation (NSIS Installer)
Start-Process ".\$Installer" -ArgumentList "/S" -Wait

# Installer löschen
Remove-Item $Installer

Write-Host "Octo Runner installed."
