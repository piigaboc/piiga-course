# CLAUDE.md

Guidance for Claude Code when working in the **piigacourse** repository.

## Agent routing (mandatory)

Route **every** task through the project-dev-agent specialists -- do not edit the codebase
directly in the main session, including small/mechanical changes (e.g. a one-line edit). The
specialists are the canonical squad maintained in `D:\claude\piiga-product-dev-agents\agents\`
(each project mirrors them into its own `.claude/agents/`). Always dispatch by the agent
*type name* (`mobile`, `frontend`, `backend`, `devops`, `designer`, `qa`, `reviewer`,
`researcher`, `lead`).

1. **Plan** -- for a multi-step feature, run `lead` first for an ordered routing plan. For a
   single, clearly-scoped change, dispatch the specialist directly.
2. **Build** -- execute each step via the assigned specialist:
   - `mobile` -- Flutter/Dart frontend, native modules, mobile tests
   - `frontend` -- React/Next/TS/Vue, browser ext, HTML/CSS/JS, frontend tests
   - `backend` -- Python services, APIs, business logic, database
   - `devops` -- CI/CD, Jenkins, Docker, deploy ยท `designer` -- UI specs/wireframes
   - `researcher` -- library/API research, prior art, technical trade-offs (reports, no prod code)
3. **Gate** -- before a substantive change is "done", run `reviewer` (correctness/security),
   then `qa` (tests). Trivial changes may skip the gate but still go through a specialist.

The main session only orchestrates (dispatch + read results), answers questions with no file
change, and runs git. Everything that edits the codebase goes through a subagent.

## Task ledger (auto-generated)

`task_dashboard.html` and `kanban_board.html` at the project root are an auto-generated task
ledger, refreshed by the `task-ledger.ps1` SubagentStop hook (wired in `.claude/settings.local.json`)
after every subagent task completes. The hook appends each dispatched task to
`.claude/agent-state/tasks.jsonl` (start) and flips it to done on completion, then re-renders both
boards via `render-task-board.ps1`. This is separate from the live agent-status board
(`.claude/agent-state/DASHBOARD.md` / `.claude/agent-state/dashboard/index.html`); do not edit the
generated HTML by hand.

**Known limitation (LIFO correlation):** `SubagentStop` carries no agent/task id, so the hook
attributes a completion to the most-recently-started task (LIFO pop of
`.claude/agent-state/.task-running`). When subagents run in **parallel** and finish out of start
order, the `agent` / `task` / `finishedAt` labels on the board can be mismatched. Total/done counts
stay correct, and it never errors or blocks dispatch -- this is the same correlation strategy as the
existing `agent-status.ps1`.
