#requires -Version 5.1
# Renders .claude/agent-state/dashboard/index.html from the per-project DASHBOARD.md table.
# DASHBOARD.md (in the REAL, non-junctioned agent-state dir) stays the source of truth;
# this just produces a viewable HTML page. Writing under agent-state keeps each project's
# live board separate and leaves the junctioned agents\dashboard\index.html (central
# overview) untouched.
$ErrorActionPreference = 'SilentlyContinue'

$md     = Join-Path $PSScriptRoot '..\agent-state\DASHBOARD.md'
$outDir = Join-Path $PSScriptRoot '..\agent-state\dashboard'
$out    = Join-Path $outDir 'index.html'

# Project name = basename of this hook's project directory (hooks -> .claude -> project root).
$projectName = Split-Path (Split-Path (Split-Path $PSScriptRoot)) -Leaf

if (-not (Test-Path $md)) { exit 0 }
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

$stamp      = ''
$colWorking = New-Object System.Collections.Generic.List[string]
$colIdle    = New-Object System.Collections.Generic.List[string]
$colBlocked = New-Object System.Collections.Generic.List[string]
$colUnused  = New-Object System.Collections.Generic.List[string]

# Per-agent left-accent colors (keyed by lowercase agent name). ASCII hex only.
$accentColors = @{
    'lead'       = '#6366f1'
    'mobile'     = '#06b6d4'
    'frontend'   = '#3b82f6'
    'backend'    = '#8b5cf6'
    'designer'   = '#ec4899'
    'qa'         = '#f97316'
    'reviewer'   = '#14b8a6'
    'researcher' = '#eab308'
    'devops'     = '#84cc16'
}

# Capitalized display labels (keyed by lowercase agent name).
$displayNames = @{
    'lead'       = 'Lead'
    'mobile'     = 'Mobile'
    'frontend'   = 'Frontend'
    'backend'    = 'Backend'
    'designer'   = 'Designer'
    'qa'         = 'QA'
    'reviewer'   = 'Reviewer'
    'researcher' = 'Researcher'
    'devops'     = 'Devops'
}

foreach ($line in (Get-Content -Path $md -Encoding utf8)) {
    if ($line -match '^_Last updated:\s*(.+?)_\s*$') { $stamp = $matches[1]; continue }

    # Table rows look like: | <emoji> `name` | role | model | tools | status | project | task |
    if ($line.StartsWith('|') -and ($line -match '`([a-z-]+)`')) {
        $name  = $matches[1]
        $cells = $line -split '\|'
        if ($cells.Count -lt 9) { continue }

        $rawDisplay = ($cells[1].Trim() -replace '`', '')
        $status     = $cells[5].Trim()
        $project    = $cells[6].Trim()
        $task       = $cells[7].Trim()

        # Keep the leading emoji, but swap the lowercase name for the capitalized label.
        $label = if ($displayNames.ContainsKey($name)) { $displayNames[$name] } else { $name }
        $display = ($rawDisplay -replace [regex]::Escape($name), $label)

        # Per-agent accent color (left bar); falls back to a neutral grey.
        $accent = if ($accentColors.ContainsKey($name)) { $accentColors[$name] } else { '#9ca3af' }

        $cls = 'unknown'
        if     ($status -match 'working') { $cls = 'working' }
        elseif ($status -match 'idle')    { $cls = 'idle' }
        elseif ($status -match 'unused')  { $cls = 'unused' }
        elseif ($status -match 'blocked') { $cls = 'blocked' }

        $cardHtml = @"
    <div class="card $cls">
      <div class="card-accent" style="background:$accent"></div>
      <div class="card-body">
        <div class="card-head">
          <span class="name">$display</span>
          <span class="badge $cls">$status</span>
        </div>
        <div class="meta-line"><span class="meta-key">Project:</span> <span class="meta-val">$project</span></div>
        <div class="meta-line"><span class="meta-key">Task:</span> <span class="meta-val">$task</span></div>
      </div>
    </div>
"@

        switch ($cls) {
            'working' { $colWorking.Add($cardHtml) }
            'idle'    { $colIdle.Add($cardHtml) }
            'blocked' { $colBlocked.Add($cardHtml) }
            'unused'  { $colUnused.Add($cardHtml) }
            default   { $colUnused.Add($cardHtml) }
        }
    }
}

# Build per-column card HTML; inject empty-state placeholder when column is empty
function Get-ColHtml {
    param([System.Collections.Generic.List[string]]$list)
    if ($list.Count -eq 0) {
        return '    <div class="card-empty">No agents</div>'
    }
    return ($list -join "`n")
}

$htmlWorking = Get-ColHtml $colWorking
$htmlIdle    = Get-ColHtml $colIdle
$htmlBlocked = Get-ColHtml $colBlocked
$htmlUnused  = Get-ColHtml $colUnused

$cntWorking = $colWorking.Count
$cntIdle    = $colIdle.Count
$cntBlocked = $colBlocked.Count
$cntUnused  = $colUnused.Count

$html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="5">
  <title>Piiga Product Dev Agents -- Status Dashboard</title>
  <style>
    /* -- Design tokens ------------------------------------------- */
    :root {
      --bg-base:       #eef0f3;
      --bg-column:     #e2e5ea;
      --bg-card:       #ffffff;
      --border-subtle: #d4d8df;
      --border-mid:    #c2c7d0;

      --text-primary:  #1f2430;
      --text-secondary:#4a5168;
      --text-muted:    #7c8499;

      /* status palette - tuned for light bg */
      --c-idle:       #16a34a;
      --c-idle-dim:   #dcfce7;
      --c-idle-border:#86efac;
      --c-idle-text:  #166534;

      --c-working:     #d97706;
      --c-working-dim: #fef3c7;
      --c-working-border:#fcd34d;
      --c-working-text:#92400e;

      --c-blocked:     #dc2626;
      --c-blocked-dim: #fee2e2;
      --c-blocked-border:#fca5a5;
      --c-blocked-text:#991b1b;

      --c-unused:      #6b7280;
      --c-unused-dim:  #f3f4f6;
      --c-unused-border:#d1d5db;
      --c-unused-text: #374151;

      --radius-card:   12px;
      --radius-col:    14px;
      --radius-badge:  999px;
      --accent-bar:    4px;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg-base);
      color: var(--text-primary);
      min-height: 100vh;
      padding: 36px 32px 48px;
      line-height: 1.5;
    }

    .page-header {
      margin-bottom: 28px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border-subtle);
    }
    .header-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    .header-titles h1 {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.3px;
      color: var(--text-primary);
    }
    .header-titles h1 span { color: var(--c-idle); }
    .sub {
      font-size: 13px;
      color: var(--text-secondary);
      margin-top: 4px;
    }
    .project-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 500;
      color: var(--text-secondary);
      background: var(--bg-card);
      border: 1px solid var(--border-mid);
      border-radius: 999px;
      padding: 5px 12px;
      white-space: nowrap;
      align-self: flex-start;
    }
    .project-chip::before {
      content: "";
      display: inline-block;
      width: 6px; height: 6px;
      border-radius: 50%;
      background: var(--c-idle);
    }

    .legend {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 18px;
    }
    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-size: 12px;
      font-weight: 500;
      padding: 4px 11px;
      border-radius: 999px;
      border: 1px solid transparent;
    }
    .legend-item.idle    { background: var(--c-idle-dim);    border-color: var(--c-idle-border);    color: var(--c-idle-text); }
    .legend-item.working { background: var(--c-working-dim); border-color: var(--c-working-border); color: var(--c-working-text); }
    .legend-item.blocked { background: var(--c-blocked-dim); border-color: var(--c-blocked-border); color: var(--c-blocked-text); }
    .legend-item.unused  { background: var(--c-unused-dim);  border-color: var(--c-unused-border);  color: var(--c-unused-text); }
    .legend-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
    .legend-item.idle    .legend-dot { background: var(--c-idle); }
    .legend-item.working .legend-dot { background: var(--c-working); }
    .legend-item.blocked .legend-dot { background: var(--c-blocked); }
    .legend-item.unused  .legend-dot { background: var(--c-unused); }

    .board {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      align-items: start;
    }
    @media (max-width: 1100px) { .board { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 600px)  { .board { grid-template-columns: 1fr; } }

    .column {
      background: var(--bg-column);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-col);
      padding: 12px 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 180px;
    }
    .col-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 4px 8px;
      border-bottom: 1px solid var(--border-subtle);
      margin-bottom: 2px;
    }
    .col-title {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.6px;
      text-transform: uppercase;
    }
    .col-title.working { color: var(--c-working); }
    .col-title.idle    { color: var(--c-idle); }
    .col-title.blocked { color: var(--c-blocked); }
    .col-title.unused  { color: var(--c-unused); }

    .col-count {
      font-size: 11px;
      font-weight: 600;
      min-width: 22px; height: 22px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 0 6px;
    }
    .col-count.working { background: var(--c-working-dim); color: var(--c-working-text); border: 1px solid var(--c-working-border); }
    .col-count.idle    { background: var(--c-idle-dim);    color: var(--c-idle-text);    border: 1px solid var(--c-idle-border); }
    .col-count.blocked { background: var(--c-blocked-dim); color: var(--c-blocked-text); border: 1px solid var(--c-blocked-border); }
    .col-count.unused  { background: var(--c-unused-dim);  color: var(--c-unused-text);  border: 1px solid var(--c-unused-border); }

    .card-empty {
      text-align: center;
      font-size: 12px;
      color: var(--text-muted);
      padding: 20px 10px;
      border: 1px dashed var(--border-mid);
      border-radius: var(--radius-card);
      background: transparent;
      font-style: italic;
    }

    .card {
      display: flex;
      flex-direction: row;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-card);
      overflow: hidden;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
      box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
    }
    .card:hover { transform: translateY(-2px); }
    .card-accent { width: var(--accent-bar); flex-shrink: 0; background: var(--c-unused); }
    .card-body { flex: 1; padding: 12px 14px 11px; min-width: 0; }

    .card.idle:hover { box-shadow: 0 6px 18px rgba(22,163,74,0.10), 0 2px 6px rgba(0,0,0,0.06); }
    .card.working {
      border-color: var(--c-working-border);
      box-shadow: 0 0 0 1px rgba(217,119,6,0.15), 0 2px 8px rgba(217,119,6,0.08);
      animation: working-pulse 2.4s ease-in-out infinite;
    }
    .card.working:hover { box-shadow: 0 0 0 1px rgba(217,119,6,0.30), 0 8px 22px rgba(217,119,6,0.12); }
    .card.blocked { border-color: var(--c-blocked-border); box-shadow: 0 0 0 1px rgba(220,38,38,0.12), 0 2px 8px rgba(220,38,38,0.06); }
    .card.blocked:hover { box-shadow: 0 0 0 1px rgba(220,38,38,0.24), 0 8px 22px rgba(220,38,38,0.08); }
    .card.unused { opacity: 0.65; }
    .card.unused:hover { opacity: 0.88; }

    @keyframes working-pulse {
      0%, 100% { box-shadow: 0 0 0 1px rgba(217,119,6,0.15), 0 2px 8px rgba(217,119,6,0.08); }
      50%       { box-shadow: 0 0 0 2px rgba(217,119,6,0.32), 0 4px 18px rgba(217,119,6,0.18); }
    }

    .card-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }
    .name {
      font-weight: 650;
      font-size: 14px;
      letter-spacing: -0.1px;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .badge {
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.2px;
      padding: 2px 9px;
      border-radius: var(--radius-badge);
      white-space: nowrap;
      flex-shrink: 0;
      border: 1px solid transparent;
    }
    .badge.idle    { background: var(--c-idle-dim);    color: var(--c-idle-text);    border-color: var(--c-idle-border); }
    .badge.working { background: var(--c-working-dim); color: var(--c-working-text); border-color: var(--c-working-border); }
    .badge.blocked { background: var(--c-blocked-dim); color: var(--c-blocked-text); border-color: var(--c-blocked-border); }
    .badge.unused  { background: var(--c-unused-dim);  color: var(--c-unused-text);  border-color: var(--c-unused-border); }

    .meta-line {
      font-size: 11.5px;
      color: var(--text-secondary);
      line-height: 1.5;
      margin-top: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .meta-line:first-of-type {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--border-subtle);
    }
    .meta-key { font-weight: 600; color: var(--text-muted); letter-spacing: 0.1px; }
    .meta-val { color: var(--text-primary); }

    .footer {
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid var(--border-subtle);
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      gap: 6px;
      align-items: center;
      flex-wrap: wrap;
    }
    .footer-sep { color: var(--border-mid); }
  </style>
</head>
<body>

  <header class="page-header">
    <div class="header-top">
      <div class="header-titles">
        <h1>Piiga Product Dev <span>Agents</span> &mdash; Status Dashboard</h1>
      </div>
      <div class="project-chip">$projectName</div>
    </div>
    <div class="legend">
      <span class="legend-item idle">   <i class="legend-dot"></i> idle</span>
      <span class="legend-item working"><i class="legend-dot"></i> working</span>
      <span class="legend-item blocked"><i class="legend-dot"></i> blocked</span>
      <span class="legend-item unused"> <i class="legend-dot"></i> not yet used</span>
    </div>
  </header>

  <div class="board">

    <div class="column">
      <div class="col-header">
        <span class="col-title working">Working</span>
        <span class="col-count working">$cntWorking</span>
      </div>
$htmlWorking
    </div>

    <div class="column">
      <div class="col-header">
        <span class="col-title idle">Idle</span>
        <span class="col-count idle">$cntIdle</span>
      </div>
$htmlIdle
    </div>

    <div class="column">
      <div class="col-header">
        <span class="col-title blocked">Blocked</span>
        <span class="col-count blocked">$cntBlocked</span>
      </div>
$htmlBlocked
    </div>

    <div class="column">
      <div class="col-header">
        <span class="col-title unused">Unused</span>
        <span class="col-count unused">$cntUnused</span>
      </div>
$htmlUnused
    </div>

  </div>

  <footer class="footer">
    <span>Last updated: $stamp</span>
    <span class="footer-sep">&middot;</span>
    <span>auto-refreshes every 5s</span>
    <span class="footer-sep">&middot;</span>
    <span>rendered from DASHBOARD.md</span>
  </footer>

</body>
</html>
"@

[System.IO.File]::WriteAllText($out, $html, (New-Object System.Text.UTF8Encoding($false)))
exit 0