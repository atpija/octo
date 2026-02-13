$Version = "0.2.0"
$BaseUrl = "https://www.project-octo.com/download/v$Version"

Write-Host "Installing Octo Client v$Version..."

$Installer = "octo-client-$Version-setup.exe"

# Datei herunterladen
Invoke-WebRequest "$BaseUrl/$Installer" -OutFile $Installer

# Silent Installation (NSIS Installer)
Start-Process ".\$Installer" -ArgumentList "/S" -Wait

# Installer löschen
Remove-Item $Installer

Write-Host "Octo Client installed."
