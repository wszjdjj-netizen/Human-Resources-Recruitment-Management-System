param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath
)

$ErrorActionPreference = "Stop"

$resolvedScript = (Resolve-Path -LiteralPath $ScriptPath).Path
$cmd = Join-Path $env:SystemRoot "System32\cmd.exe"
$key = "HKCU:\Software\Classes\recruitment-runner"
$commandKey = Join-Path $key "shell\open\command"

New-Item -Path $key -Force | Out-Null
Set-ItemProperty -Path $key -Name "(default)" -Value "URL:Recruitment Runner Protocol"
New-ItemProperty -Path $key -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null

New-Item -Path $commandKey -Force | Out-Null
$command = "`"$cmd`" /d /c `"`"$resolvedScript`" `"%1`"`""
Set-ItemProperty -Path $commandKey -Name "(default)" -Value $command

Write-Host "Registered command:"
Write-Host $command
