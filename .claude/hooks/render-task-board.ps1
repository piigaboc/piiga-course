#requires -Version 5.1
# Renders the task-history boards from .claude/agent-state/tasks.jsonl into TWO static files at
# the PROJECT ROOT:
#   task_dashboard.html : stats row (total / done / in-progress) + a newest-first table.
#   kanban_board.html   : columns by status (Planned / Backlog / In Progress / Done).
# Styled after the LF_Data_Builder_Pipeline reference boards. Pure static HTML, inline CSS,
# UTF-8 no BOM, no external dependencies. Empty ledger renders cleanly (0 stats / empty cols).
$ErrorActionPreference = 'SilentlyContinue'

$ledger     = Join-Path $PSScriptRoot '..\agent-state\tasks.jsonl'
$projectDir = Split-Path (Split-Path $PSScriptRoot)        # hooks -> .claude -> project root
$projectName = Split-Path $projectDir -Leaf
$dashOut    = Join-Path $projectDir 'task_dashboard.html'
$kanbanOut  = Join-Path $projectDir 'kanban_board.html'
$utf8       = New-Object System.Text.UTF8Encoding($false)
$stamp      = (Get-Date).ToString('yyyy-MM-dd HH:mm')

# ---- Load + parse ledger (newest first) -------------------------------------
$records = New-Object System.Collections.Generic.List[object]
if (Test-Path $ledger) {
    foreach ($l in (Get-Content -Path $ledger -Encoding utf8)) {
        if ($l -eq $null -or $l.Trim() -eq '') { continue }
        $obj = $null
        try { $obj = $l | ConvertFrom-Json } catch { }
        if ($obj -and $obj.id) { $records.Add($obj) }
    }
}
# Newest first. (Build a reversed list explicitly; @(List[object]) + [array]::Reverse
# is not reliable under PS 5.1, so iterate from the end.)
$ordered = New-Object System.Collections.Generic.List[object]
for ($i = $records.Count - 1; $i -ge 0; $i--) { $ordered.Add($records[$i]) }

$total = $ordered.Count
$cntDone = @($ordered | Where-Object { $_.status -eq 'done' }).Count
$cntProg = @($ordered | Where-Object { $_.status -ne 'done' }).Count

function Esc {
    param([string]$s)
    if ($null -eq $s) { return '' }
    $s = $s -replace '&', '&amp;'
    $s = $s -replace '<', '&lt;'
    $s = $s -replace '>', '&gt;'
    $s = $s -replace '"', '&quot;'
    return $s
}

# ============================================================================
# 1) task_dashboard.html
# ============================================================================
$rowsHtml = New-Object System.Collections.Generic.List[string]
foreach ($r in $ordered) {
    $statusClass = if ($r.status -eq 'done') { 'done' } else { 'prog' }
    $statusLabel = if ($r.status -eq 'done') { 'done' } else { 'in-progress' }
    $fin = if ($r.finishedAt) { Esc ([string]$r.finishedAt) } else { [char]0x2014 }
    $rowsHtml.Add(@"
    <tr>
      <td><code>$(Esc ([string]$r.id))</code></td>
      <td><span class="agent">$(Esc ([string]$r.agent))</span></td>
      <td>$(Esc ([string]$r.task))</td>
      <td><span class="pill $statusClass">$statusLabel</span></td>
      <td class="result">$(Esc ([string]$r.startedAt))</td>
      <td class="result">$fin</td>
    </tr>
"@)
}
$tableBody = if ($rowsHtml.Count -gt 0) { ($rowsHtml -join "`n") } else {
    '    <tr><td colspan="6" class="empty">No tasks recorded yet.</td></tr>'
}

$dashHtml = @"
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>$projectName &middot; Task Dashboard</title>
<style>
  :root{
    --bg:#f4f7f5; --surface:#fff; --border:#e2e8e5; --text:#16201b; --muted:#5b6b63;
    --primary:#13784a; --primary-soft:#e3f2ea; --primary-hover:#0f6b43;
    --warn:#b9770e; --warn-soft:#fdf3e0;
    --radius:14px; --shadow:0 10px 30px -18px rgba(22,32,27,.5);
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.5}
  .wrap{max-width:1120px;margin:0 auto;padding:32px 20px 64px}
  header{display:flex;flex-wrap:wrap;align-items:baseline;gap:12px 18px;margin-bottom:6px}
  h1{font-size:1.7rem;margin:0}
  .sub{color:var(--muted);margin:2px 0 0}
  .meta{margin-left:auto;color:var(--muted);font-size:.85rem;text-align:right}
  .pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.72rem;font-weight:600;
    letter-spacing:.02em;border:1px solid transparent;white-space:nowrap}
  .pill.done{background:var(--primary-soft);color:var(--primary-hover);border-color:#bfe0cf}
  .pill.prog{background:var(--warn-soft);color:var(--warn);border-color:#f3d9a6}

  .stat-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;margin:22px 0 28px}
  .stat{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
    padding:16px 18px;box-shadow:var(--shadow)}
  .stat .n{font-size:1.5rem;font-weight:700;line-height:1}
  .stat .l{color:var(--muted);font-size:.78rem;margin-top:6px}

  h2{font-size:1.05rem;margin:30px 0 12px;display:flex;align-items:center;gap:8px}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
    box-shadow:var(--shadow);overflow:hidden}
  table{width:100%;border-collapse:collapse;font-size:.9rem}
  th,td{text-align:left;padding:12px 16px;vertical-align:top;border-bottom:1px solid var(--border)}
  th{background:#fafcfb;color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em}
  tr:last-child td{border-bottom:none}
  td .agent{font-weight:600;white-space:nowrap}
  td.result{color:var(--muted);white-space:nowrap}
  td.empty{color:var(--muted);font-style:italic;text-align:center;padding:28px 16px}
  code{font-family:var(--mono);font-size:.82em;background:#eef2f0;padding:1px 6px;border-radius:6px}
  a{color:var(--primary-hover)}
  .foot{color:var(--muted);font-size:.8rem;margin-top:28px;text-align:center}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div>
      <h1>$projectName &mdash; Task Dashboard</h1>
      <p class="sub">Auto-generated task ledger &middot; sourced from <code>.claude/agent-state/tasks.jsonl</code></p>
    </div>
    <div class="meta">
      Last updated $stamp
    </div>
  </header>

  <div class="stat-row">
    <div class="stat"><div class="n">$total</div><div class="l">Total tasks</div></div>
    <div class="stat"><div class="n">$cntDone</div><div class="l">Done</div></div>
    <div class="stat"><div class="n">$cntProg</div><div class="l">In progress</div></div>
  </div>

  <h2>Task history</h2>
  <div class="card"><table>
    <tr><th>ID</th><th>Agent</th><th>Task</th><th>Status</th><th>Started</th><th>Finished</th></tr>
$tableBody
  </table></div>

  <p class="foot">Auto-generated by the task-ledger SubagentStop hook &middot; companion: <a href="kanban_board.html">kanban_board.html</a></p>
</div>
</body>
</html>
"@
[System.IO.File]::WriteAllText($dashOut, $dashHtml, $utf8)

# ============================================================================
# 2) kanban_board.html  (server-rendered cards, LF visual style, 4 columns)
# ============================================================================
function Build-Cards {
    param([string]$colKey, [string]$colorVar)
    $items = @($ordered | Where-Object {
        if ($colKey -eq 'done') { $_.status -eq 'done' }
        elseif ($colKey -eq 'inprogress') { $_.status -ne 'done' }
        else { $false }
    })
    if ($items.Count -eq 0) {
        return @{ count = 0; html = '    <div class="empty-col">&mdash;</div>' }
    }
    $cards = New-Object System.Collections.Generic.List[string]
    foreach ($r in $items) {
        $cards.Add(@"
      <div class="card" style="border-left-color:$colorVar">
        <div class="name">$(Esc ([string]$r.task))<span class="order">$(Esc ([string]$r.id))</span></div>
        <div class="role">$(Esc ([string]$r.agent))</div>
        <div class="tags"><span class="tag">$(Esc ([string]$r.agent))</span></div>
      </div>
"@)
    }
    return @{ count = $items.Count; html = ($cards -join "`n") }
}

$plannedCol = @{ count = 0; html = '    <div class="empty-col">&mdash;</div>' }
$backlogCol = @{ count = 0; html = '    <div class="empty-col">&mdash;</div>' }
$progCol    = Build-Cards 'inprogress' 'var(--progress)'
$doneCol    = Build-Cards 'done'       'var(--done)'

$kanbanHtml = @"
<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>$projectName &middot; Kanban</title>
<style>
  :root {
    --bg: #e9ebee;
    --panel: #f5f6f8;
    --panel-2: #ffffff;
    --border: #d3d7de;
    --text: #1f2430;
    --muted: #6b7280;
    --planned: #6b7280;
    --backlog: #a855f7;
    --progress: #3b82f6;
    --done: #22c55e;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
  }
  header {
    padding: 20px 28px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: baseline;
    gap: 16px;
    flex-wrap: wrap;
  }
  header h1 { font-size: 18px; margin: 0; font-weight: 650; }
  header .project { color: var(--progress); font-weight: 600; }
  header .meta { color: var(--muted); font-size: 13px; margin-left: auto; display: flex; gap: 14px; align-items: center; }
  .board {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    padding: 24px 28px;
    align-items: start;
  }
  @media (max-width:1080px){.board{grid-template-columns:repeat(2,1fr)}}
  @media (max-width:640px){.board{grid-template-columns:1fr}}
  .column {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px;
    min-height: 120px;
  }
  .column h2 {
    font-size: 13px; text-transform: uppercase; letter-spacing: .06em;
    margin: 0 0 14px; display: flex; align-items: center; gap: 8px; color: var(--muted);
  }
  .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
  .count { margin-left: auto; background: var(--panel-2); color: var(--muted);
           border-radius: 20px; padding: 1px 9px; font-size: 12px; }
  .card {
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-left-width: 3px;
    border-radius: 9px;
    padding: 12px 13px;
    margin-bottom: 11px;
  }
  .card:last-child { margin-bottom: 0; }
  .card .name { font-weight: 650; font-size: 14px; display: flex; align-items: center; gap: 8px; }
  .card .order { color: var(--muted); font-size: 11px; font-weight: 600;
                 background: var(--panel); border-radius: 5px; padding: 1px 6px; margin-left: auto; }
  .card .role { color: var(--muted); font-size: 12px; margin: 6px 0 8px; line-height: 1.4; }
  .tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 9px; }
  .tag { font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 20px;
         background: var(--panel); color: var(--muted); border: 1px solid var(--border); }
  .empty-col { color: var(--muted); font-size: 13px; font-style: italic; padding: 4px; }
  footer { color: var(--muted); font-size: 12px; padding: 4px 28px 28px; }
  code { background: var(--panel-2); padding: 1px 6px; border-radius: 5px; }
  a { color: var(--progress); }
</style>
</head>
<body>
<header>
  <h1>$projectName &middot; <span class="project">Kanban</span></h1>
  <div class="meta">
    <span>updated $stamp</span>
  </div>
</header>

<div class="board">
  <div class="column">
    <h2><span class="dot" style="background:var(--planned)"></span>Planned<span class="count">$($plannedCol.count)</span></h2>
$($plannedCol.html)
  </div>
  <div class="column">
    <h2><span class="dot" style="background:var(--backlog)"></span>Backlog<span class="count">$($backlogCol.count)</span></h2>
$($backlogCol.html)
  </div>
  <div class="column">
    <h2><span class="dot" style="background:var(--progress)"></span>In Progress<span class="count">$($progCol.count)</span></h2>
$($progCol.html)
  </div>
  <div class="column">
    <h2><span class="dot" style="background:var(--done)"></span>Done<span class="count">$($doneCol.count)</span></h2>
$($doneCol.html)
  </div>
</div>
<footer>Auto-generated task ledger &middot; columns derived from task status &middot; see also <a href="task_dashboard.html">task_dashboard.html</a>.</footer>
</body>
</html>
"@
[System.IO.File]::WriteAllText($kanbanOut, $kanbanHtml, $utf8)

exit 0
