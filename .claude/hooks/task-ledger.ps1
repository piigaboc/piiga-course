#requires -Version 5.1
# Maintains an append-only task ledger (.claude/agent-state/tasks.jsonl) and re-renders the
# task-history boards (task_dashboard.html + kanban_board.html at the project root).
# This is SEPARATE from the live agent-status board (agent-status.ps1 / DASHBOARD.md);
# it uses its own queue file (.task-running) so the two mechanisms never collide.
#
#   -Status start : called from PreToolUse(Task/Agent). Reads subagent_type from stdin JSON
#                   (exits 0 if absent), appends an "in-progress" record, and pushes the new
#                   record id onto the .task-running queue so the stop hook can correlate.
#   -Status done  : called from SubagentStop. SubagentStop stdin has no subagent_type/id, so
#                   we pop the LAST id off the .task-running queue, flip that record to "done"
#                   with finishedAt = now, rewrite the ledger, then re-render the boards.
param([Parameter(Mandatory = $true)][ValidateSet('start', 'done')][string]$Status)

$ErrorActionPreference = 'SilentlyContinue'

$ledger = Join-Path $PSScriptRoot '..\agent-state\tasks.jsonl'
$queue  = Join-Path $PSScriptRoot '..\agent-state\.task-running'
$utf8   = New-Object System.Text.UTF8Encoding($false)

# Per-project runtime state lives in a REAL (non-junctioned) .claude\agent-state dir,
# separate from the shared (junctioned) .claude\agents definitions. Ensure it exists
# before the first write so appends never fail on a fresh project.
$stateDir = Split-Path $ledger
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

if ($Status -eq 'start') {
    $agent = $null
    if ($json -and $json.tool_input -and $json.tool_input.subagent_type) {
        $agent = [string]$json.tool_input.subagent_type
    }
    if (-not $agent) { exit 0 }

    # Task = description, else first line of prompt, else em-dash.
    $task = ''
    if ($json -and $json.tool_input -and $json.tool_input.description) {
        $task = ([string]$json.tool_input.description).Trim()
    }
    elseif ($json -and $json.tool_input -and $json.tool_input.prompt) {
        $task = (([string]$json.tool_input.prompt) -split "`n")[0].Trim()
    }
    if (-not $task) { $task = [char]0x2014 }  # em-dash

    $id  = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + $agent
    $now = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')

    $record = [ordered]@{
        id         = $id
        agent      = $agent
        task       = $task
        status     = 'in-progress'
        startedAt  = $now
        finishedAt = ''
    }
    $line = ($record | ConvertTo-Json -Compress)
    # BOM-less append: Add-Content -Encoding utf8 under PS 5.1 writes a UTF-8 BOM that
    # corrupts the first record/id and breaks id correlation on the done path.
    [System.IO.File]::AppendAllText($ledger, $line + "`r`n", $utf8)

    # Push id onto the running queue (one id per line), BOM-less for the same reason.
    [System.IO.File]::AppendAllText($queue, $id + "`r`n", $utf8)

    # Refresh the central cross-project overview (agent-status.ps1 has already
    # updated this project's DASHBOARD.md by the time this hook runs).
    $overview = 'D:\claude\piiga-product-dev-agents\hooks\render-overview.ps1'
    if (Test-Path $overview) { & $overview }
    exit 0
}

# -Status done : pop the most-recent id off the queue.
$id = $null
if (Test-Path $queue) {
    $ids = @(Get-Content $queue -Encoding utf8 | Where-Object { $_ -ne '' })
    if ($ids.Count -gt 0) {
        $id = $ids[-1].Trim()
        if ($ids.Count -gt 1) {
            [System.IO.File]::WriteAllLines($queue, $ids[0..($ids.Count - 2)], $utf8)
        } else {
            Remove-Item -Path $queue -Force
        }
    }
}
if (-not $id) { exit 0 }
if (-not (Test-Path $ledger)) { exit 0 }

$now = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
$out = New-Object System.Collections.Generic.List[string]
foreach ($l in (Get-Content -Path $ledger -Encoding utf8)) {
    if ($l -eq $null -or $l.Trim() -eq '') { continue }
    $obj = $null
    try { $obj = $l | ConvertFrom-Json } catch { }
    if ($obj -and $obj.id -eq $id -and $obj.status -ne 'done') {
        $obj.status = 'done'
        $obj.finishedAt = $now
        $out.Add(($obj | ConvertTo-Json -Compress))
    } else {
        $out.Add($l)
    }
}
[System.IO.File]::WriteAllLines($ledger, $out, $utf8)

# Re-render the boards from the updated ledger.
$render = Join-Path $PSScriptRoot 'render-task-board.ps1'
if (Test-Path $render) { & $render }

# Refresh the central cross-project overview (DASHBOARD.md already current).
$overview = 'D:\claude\piiga-product-dev-agents\hooks\render-overview.ps1'
if (Test-Path $overview) { & $overview }

exit 0