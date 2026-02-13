$Version = "0.2.0"
$BaseUrl = "https://github.com/atpija/octo/releases/download/v$Version"

Write-Host "Installing Octo Client v$Version..."

$Installer = "octo-client-$Version-setup.exe"

Invoke-WebRequest "$BaseUrl/$Installer" -OutFile $Installer

Start-Process ".\$Installer" -ArgumentList "/S" -Wait

Remove-Item $Installer

Write-Host "Octo Client installed."