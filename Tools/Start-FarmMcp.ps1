param(
    [string]$EngineRoot,
    [int]$Port = 8000,
    [switch]$Render
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$projectFile = Join-Path $projectRoot 'FarmSim25D.uproject'
if (-not $EngineRoot) {
    $descriptor = Get-Content -LiteralPath $projectFile -Raw | ConvertFrom-Json
    $installs = Get-Content -LiteralPath 'C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat' -Raw | ConvertFrom-Json
    $EngineRoot = ($installs.InstallationList | Where-Object ArtifactId -eq ('UE_' + $descriptor.EngineAssociation) | Select-Object -First 1).InstallLocation
}
if (-not $EngineRoot) { throw 'Pass -EngineRoot with the UE 5.8 installation directory.' }
$editorExe = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
if (-not (Test-Path -LiteralPath $editorExe)) { throw "Editor not found: $editorExe" }
$existing = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -like "*$projectFile*" }
if ($existing) { throw 'This project already has an editor process. Reuse that instance or stop it before starting another writer.' }
$logDirectory = Join-Path $projectRoot 'Saved\Logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$logFile = Join-Path $logDirectory 'FarmMCP_Background.log'
$rhiFlag = if ($Render) { '' } else { '-nullrhi' }
$editorArgs = '"{0}" -unattended -RenderOffscreen {1} -nosplash -nosound -NoLoadingScreen -NoLogWindow -ModelContextProtocolStartServer -ModelContextProtocolPort={2} -abslog="{3}" -ExecCmds="t.MaxFPS 10"' -f $projectFile,$rhiFlag,$Port,$logFile
$editorProcess = Start-Process -FilePath $editorExe -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
$editorProcess.PriorityClass = 'BelowNormal'
[pscustomobject]@{ ProcessId=$editorProcess.Id; Endpoint="http://127.0.0.1:$Port/mcp"; Log=$logFile; OffscreenRendering=[bool]$Render }
