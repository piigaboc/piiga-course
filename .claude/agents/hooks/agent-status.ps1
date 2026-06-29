#requires -Version 5.1
# Shared hub hook: updates the product-dev-agents status dashboard when a
# subagent starts/stops, from ANY linked project. Every project's
# settings.local.json calls this one script by absolute path, so there is a
# single source of truth and one shared dashboard.
#
#   -Status working : PreToolUse(Task/Agent). Reads subagent_type from stdin JSON,
#                     marks that agent row 🟡 working, records it on a running-queue,
#                     and fills Project (from the hook's cwd) + Task.
#   -Status idle    : SubagentStop. Pops the most-recent agent off the queue and
#                     marks its row 🟢 idle, resetting Project + Task to em-dash.
#                     (SubagentStop input has no subagent_type, so we rely on the
#                     queue written at start time. The queue is shared, so it is a
#                     LIFO across all projects — fine for sequential routing.)
param([Parameter(Mandatory = $true)][ValidateSet('working', 'idle')][string]$Status)

$ErrorActionPreference = 'SilentlyContinue'

# This script lives in agents/hooks; the dashboard data sits one level up.
$dashboard = Join-Path $PSScriptRoot '..\DASHBOARD.md'
$queue     = Join-Path $PSScriptRoot '..\.running'

# Read hook stdin (JSON). May be empty for some events.
$raw = [Console]::In.ReadToEnd()
$json = $null
if ($raw) { try { $json = $raw | ConvertFrom-Json } catch { } }

# Em dash (U+2014) via code point — a raw '—' literal gets mangled because PS 5.1
# reads this BOM-less UTF-8 script through the system ANSI codepage.
$dash    = [char]0x2014
$agent   = $null
$project = $dash
$task    = $dash
if ($Status -eq 'working') {
    if ($json -and $json.tool_input -and $json.tool_input.subagent_type) {
        $agent = [string]$json.tool_input.subagent_type
    }
    if (-not $agent) { exit 0 }
    Add-Content -Path $queue -Value $agent -Encoding utf8

    # Project = basename of the invoking project's working dir (from the hook payload).
    if ($json -and $json.cwd) { $project = Split-Path ([string]$json.cwd) -Leaf }

    # Task = description, else first line of prompt, else em-dash.
    if ($json -and $json.tool_input -and $json.tool_input.description) {
        $task = ([string]$json.tool_input.description).Trim()
    }
    elseif ($json -and $json.tool_input -and $json.tool_input.prompt) {
        $task = (([string]$json.tool_input.prompt) -split "`n")[0].Trim()
    }
    if (-not $task) { $task = $dash }
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
