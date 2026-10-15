$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$root = Split-Path $PSScriptRoot -Parent
$redist = Join-Path $PSScriptRoot 'redist'
New-Item -ItemType Directory -Path $redist -Force | Out-Null
$packages = @(
    @{Name='HidHide_1.5.230_x64.exe'; URL='https://github.com/nefarius/HidHide/releases/download/v1.5.230.0/HidHide_1.5.230_x64.exe'},
    @{Name='ViGEmBus_1.22.0_x64_x86_arm64.exe'; URL='https://github.com/nefarius/ViGEmBus/releases/download/v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe'}
)
$records = @()
foreach ($package in $packages) {
    $destination = Join-Path $redist $package.Name
    if (-not (Test-Path $destination)) {
        Write-Host ('Downloading official driver installer: ' + $package.Name)
        Invoke-WebRequest -UseBasicParsing -Uri $package.URL -OutFile ($destination + '.download')
        Move-Item -LiteralPath ($destination + '.download') -Destination $destination -Force
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $destination
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Nefarius') {
        throw ('Driver signature verification failed: ' + $destination + '. No installer will be built.')
    }
    $records += @{File=$package.Name; URL=$package.URL; SHA256=(Get-FileHash $destination -Algorithm SHA256).Hash; Signer=$signature.SignerCertificate.Subject}
}
ConvertTo-Json -InputObject $records | Set-Content -Encoding UTF8 (Join-Path $redist 'verified-downloads.json')
$compilerPaths = @(
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $compilerPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    $found = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($found) { $iscc = $found.Source }
}
if (-not $iscc) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) { throw 'Install Inno Setup 6.3 or newer from https://jrsoftware.org/isdl.php, then run BUILD_SETUP.bat again.' }
    Write-Host 'Installing the Inno Setup compiler. Windows may ask for permission.'
    & $winget.Source install --id JRSoftware.InnoSetup --exact --source winget --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup installation failed. Install it from https://jrsoftware.org/isdl.php and retry.' }
    $iscc = $compilerPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) { throw 'ISCC.exe was not found. Restart the terminal after installing Inno Setup and retry.' }
& $iscc (Join-Path $PSScriptRoot 'AutoY.iss')
if ($LASTEXITCODE -ne 0) { throw 'Setup compilation failed.' }
