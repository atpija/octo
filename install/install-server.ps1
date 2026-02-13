$Version = "0.2.0"
$BaseUrl = "https://github.com/atpija/octo/releases/download/v$Version"

Write-Host "Installing Octo Server v$Version..."

$Installer = "octo-server-$Version-setup.exe"

Invoke-WebRequest "$BaseUrl/$Installer" -OutFile $Installer

Start-Process ".\$Installer" -ArgumentList "/S" -Wait

Remove-Item $Installer

Write-Host "Octo Server installed."