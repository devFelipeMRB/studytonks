# Real Windows smoke: installation, upgrade, bundled Qt app, data and uninstall.
# Always use a unique temporary installation path; never install over a real app.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$setup = Join-Path $root 'dist\release\Studytonks-Setup.exe'
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('studytonks-installer-test-' + [guid]::NewGuid())
$destination = Join-Path $temporary 'Installed'
$installLog = Join-Path $root 'dist\installer-test-install.log'
$uninstallLog = Join-Path $root 'dist\installer-test-uninstall.log'
$dataDirectory = Join-Path $env:APPDATA 'Studytonks'
$dataExisted = Test-Path $dataDirectory
$marker = Join-Path $dataDirectory ('installer-preservation-' + [guid]::NewGuid() + '.json')
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$existingStartup = Get-ItemProperty -Path $runKey -Name 'Studytonks' -ErrorAction SilentlyContinue
$uninstaller = Join-Path $destination 'unins000.exe'
$previousPlatform = $env:QT_QPA_PLATFORM
$ownStartup = $false

function Invoke-CheckedProcess([string]$File, [string[]]$Arguments, [int]$Timeout = 120000) {
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $File
    $startInfo.Arguments = $Arguments -join ' '
    $startInfo.UseShellExecute = $false
    $process = [System.Diagnostics.Process]::Start($startInfo)
    try {
        if (-not $process.WaitForExit($Timeout)) {
            $process.Kill()
            $process.WaitForExit()
            throw "Timed out: $File"
        }
        if ($process.ExitCode -ne 0) {
            throw "Process exited with code $($process.ExitCode): $File"
        }
    }
    finally {
        $process.Dispose()
    }
}

try {
    if (-not (Test-Path $setup)) { throw 'Installer was not built.' }
    $uninstallId = '{78BB0D3E-9A36-441D-AC4B-D49AE2384D27}_is1'
    foreach ($hive in @('HKCU:', 'HKLM:')) {
        if (Test-Path "$hive\Software\Microsoft\Windows\CurrentVersion\Uninstall\$uninstallId") {
            throw 'A real Studytonks installation already exists. Run this installer check only on a clean Windows test machine.'
        }
    }
    New-Item -ItemType Directory -Force -Path $temporary, $dataDirectory | Out-Null
    Set-Content -LiteralPath $marker -Value '{"preserve":true}' -Encoding utf8
    $installerArguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
        '/NOICONS', "/DIR=`"$destination`"", "/LOG=`"$installLog`"")
    Invoke-CheckedProcess $setup $installerArguments
    $executable = Join-Path $destination 'Studytonks.exe'
    if (-not (Test-Path $executable)) { throw 'Installer did not install the executable.' }
    if (-not (Test-Path (Join-Path $destination '_internal'))) { throw 'Bundled dependencies missing.' }
    $startupAfter = Get-ItemProperty -Path $runKey -Name 'Studytonks' -ErrorAction SilentlyContinue
    if ($startupAfter.Studytonks -ne $existingStartup.Studytonks) { throw 'Installer modified startup without consent.' }
    $env:QT_QPA_PLATFORM = 'offscreen'
    Invoke-CheckedProcess $executable @('--smoke-test') 60000
    # Reinstall in place to verify the supported update path.
    Invoke-CheckedProcess $setup $installerArguments
    Invoke-CheckedProcess $executable @('--smoke-test') 60000
    if (-not (Test-Path $marker)) { throw 'Update removed persistent data.' }

    # A CI run owns no user startup setting. Exercise cleanup only if it is unset.
    if ($null -eq $existingStartup) {
        New-Item -Path $runKey -Force | Out-Null
        New-ItemProperty -Path $runKey -Name 'Studytonks' -PropertyType String -Value "`"$executable`"" | Out-Null
        $ownStartup = $true
    }
    Invoke-CheckedProcess $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=`"$uninstallLog`"")
    if (Test-Path $executable) { throw 'Uninstaller left the application executable.' }
    if (-not (Test-Path $marker)) { throw 'Uninstaller deleted personal data.' }
    if ($ownStartup -and (Get-ItemProperty -Path $runKey -Name 'Studytonks' -ErrorAction SilentlyContinue)) {
        throw 'Uninstaller left its own startup registration.'
    }
    Write-Host 'Installation, bundled GUI, update, startup consent and data preservation passed.'
}
finally {
    $env:QT_QPA_PLATFORM = $previousPlatform
    if (Test-Path $uninstaller) {
        try { Invoke-CheckedProcess $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') } catch { Write-Warning $_ }
    }
    if ($ownStartup) {
        $startup = Get-ItemProperty -Path $runKey -Name 'Studytonks' -ErrorAction SilentlyContinue
        if ($startup.Studytonks -eq "`"$destination\Studytonks.exe`"") {
            Remove-ItemProperty -Path $runKey -Name 'Studytonks'
        }
    }
    if (Test-Path $marker) { Remove-Item -LiteralPath $marker }
    if (-not $dataExisted -and (Test-Path $dataDirectory) -and
        @(Get-ChildItem -LiteralPath $dataDirectory -Force).Count -eq 0) {
        Remove-Item -LiteralPath $dataDirectory
    }
    if (Test-Path $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
}
