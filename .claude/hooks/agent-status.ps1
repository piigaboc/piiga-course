#requires -Version 5.1
# Updates the product-dev-agents status dashboard when a subagent starts/stops.
#   -Status working : called from PreToolUse(Task/Agent); reads subagent_type from stdin JSON,
#                     marks that agent row 🟡 working, records it on a running-queue file, and
#                     populates the Project + Task cells.
#   -Status idle    : called from SubagentStop; pops the most-recent agent off the queue and
#                     marks its row 🟢 idle, resetting Project + Task to em-dash. (SubagentStop
#                     input has no subagent_type, so we rely on the queue written at start time.)
param([Parameter(Mandatory = $true)][ValidateSet('working', 'idle')][string]$Status)

$ErrorActionPreference = 'SilentlyContinue'

$dashboard = Join-Path $PSScriptRoot '..\agent-state\DASHBOARD.md'
$queue     = Join-Path $PSScriptRoot '..\agent-state\.running'

# Per-project runtime state lives in a REAL (non-junctioned) .claude\agent-state dir,
# separate from the shared (junctioned) .claude\agents definitions. Ensure it exists.
$stateDir = Split-Path $dashboard
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }

# Read hook stdin (JSON) FIRST. May be empty for some events / manual runs.
$raw = [Console]::In.ReadToEnd()
$json = $null
if ($raw) { try { $json = $raw | ConvertFrom-Json } catch { } }

# Only act for the session's own project. The hook stdin carries the session cwd; when this
# script was loaded via another project's additionalDirectories, $json.cwd points at the
# SESSION project, not this script's project, so we skip to prevent cross-project leakage.
$myProjectDir = Split-Path (Split-Path $PSScriptRoot)   # hooks -> .claude -> project root
if ($json -and $json.cwd) {
    $a = [System.IO.Path]::GetFullPath([string]$myProjectDir).TrimEnd('\')
    $b = [System.IO.Path]::GetFullPath([string]$json.cwd).TrimEnd('\')
    if (-not ($a -ieq $b)) { exit 0 }
}

# Em-dash placeholder built from its code point (U+2014) so rewrites stay UTF-8 clean
# and never produce mojibake from a literal char in this script's body.
$emDash  = [char]::ConvertFromUtf32(0x2014)
$agent = $null
$project = $emDash
$task    = $emDash
if ($Status -eq 'working') {
    if ($json -and $json.tool_input -and $json.tool_input.subagent_type) {
        $agent = [string]$json.tool_input.subagent_type
    }
    if (-not $agent) { exit 0 }
    Add-Content -Path $queue -Value $agent -Encoding utf8

    # Project = basename of this hook's project directory (hooks -> .claude -> project).
    $project = Split-Path (Split-Path (Split-Path $PSScriptRoot)) -Leaf

    # Task = description, else first line of prompt, else em-dash.
    if ($json -and $json.tool_input -and $json.tool_input.description) {
        $task = ([string]$json.tool_input.description).Trim()
    }
    elseif ($json -and $json.tool_input -and $json.tool_input.prompt) {
        $task = (([string]$json.tool_input.prompt) -split "`n")[0].Trim()
    }
    if (-not $task) { $task = $emDash }
}
else {
    # Prefer subagent_type if the event happens to carry it; otherwise pop the queue.
    if ($json -and $json.subagent_type) { $agent = [string]$json.subagent_type }
    if (-not $agent -and (Test-Path $queue)) {
        $lines = @(Get-Content $queue | Where-Object { $_ -ne '' })
        if ($lines.Count -gt 0) {
            $agent = $lines[-1].Trim()
            if ($lines.Count -gt 1) {
                Set-Content -Path $queue -Value $lines[0..($lines.Count - 2)] -Encoding utf8
            } else {
                Remove-Item -Path $queue -Force
            }
        }
    }
    if (-not $agent) { exit 0 }
}

if (-not (Test-Path $dashboard)) { exit 0 }

# Build the status emoji from code points so it doesn't depend on how PS reads this script's encoding.
# 🟡 = U+1F7E1 (working), 🟢 = U+1F7E2 (idle).
$emoji = if ($Status -eq 'working') {
    [char]::ConvertFromUtf32(0x1F7E1) + ' working'
} else {
    [char]::ConvertFromUtf32(0x1F7E2) + ' idle'
}
$stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm')
$token = '`' + $agent + '`'   # agent name appears backticked in the table, e.g. `mobile`

$out = foreach ($line in (Get-Content -Path $dashboard -Encoding utf8)) {
    if ($line.StartsWith('|') -and $line.Contains($token)) {
        $cells = $line -split '\|'
        # cells: '', agent(1), role(2), model(3), tools(4), status(5), project(6), task(7), ''
        if ($cells.Count -ge 9) {
            $cells[5] = " $emoji "
            $cells[6] = " $project "
            $cells[7] = " $task "
            $line = ($cells -join '|')
        }
    }
    elseif ($line -match '^_Last updated:') {
        $line = "_Last updated: ${stamp}_"
    }
    $line
}

# Write UTF-8 without BOM so the markdown stays clean across repeated rewrites.
[System.IO.File]::WriteAllLines($dashboard, $out, (New-Object System.Text.UTF8Encoding($false)))

# Regenerate the HTML view from the updated markdown.
$render = Join-Path $PSScriptRoot 'render-dashboard.ps1'
if (Test-Path $render) { & $render }

exit 0
