# Product Dev Agents — Status Dashboard

Squad of project-scoped agents for **Shrinkage Management System (SF) frontend** — a Flutter/Dart app.
Defined in `.claude/agents/`. Status legend: 🟢 idle/ready · 🟡 working · 🔴 blocked · ⚪ not yet used.

> Note: subagents can't spawn other subagents — the main session orchestrates. The `lead` agent plans
> and routes; the main session executes each step via the assigned specialist.

| Agent | Role | Model | Tools | Status | Project | Task |
|-------|------|-------|-------|--------|---------|------|
| 🧭 `lead` | Tech lead / orchestrator — decomposes features, routes steps to specialists (plan only) | opus | Read, Glob, Grep | 🟢 idle | — | — |
| 📱 `mobile` | Flutter/Dart, iOS/Android native modules, mobile unit tests | opus | Read, Write, Edit, Glob, Grep, Bash | 🟢 idle | — | — |
| 🖥️ `frontend` | React/Next/TS/Vue, browser ext, HTML/CSS/JS, frontend unit tests | opus | Read, Write, Edit, Glob, Grep, Bash | 🟢 idle | — | — |
| ⚙️ `backend` | Python services, DB schema/queries, business logic, API design | opus | Read, Write, Edit, Glob, Grep, Bash | 🟢 idle | — | — |
| 🎨 `designer` | Design specs, wireframes, component specs, design tokens, a11y review | opus | Read, Write, Glob, Grep | 🟢 idle | — | — |
| 🧪 `qa` | Integration/E2E tests, edge-case analysis, regression suites | opus | Read, Write, Edit, Glob, Grep, Bash | 🟢 idle | — | — |
| 🔍 `reviewer` | Correctness, code quality, security, perf review (gate before release) | opus | Read, Glob, Grep, Bash | 🟢 idle | — | — |
| 🔬 `researcher` | Library/API research, prior art, technical trade-offs (reports, no prod code) | opus | Read, Glob, Grep, WebFetch, WebSearch | 🟢 idle | — | — |
| 🚀 `devops` | CI/CD, Jenkins, Docker, deployment, env config | opus | Read, Write, Edit, Glob, Grep, Bash | 🟢 idle | — | — |

## How work flows

1. **Plan** — `lead` decomposes a feature into ordered steps, each assigned to one specialist.
2. **Build** — main session runs each step via the assigned agent (parallel where independent).
3. **Gate** — `reviewer` (correctness/security) then `qa` (tests) before a feature is "done".

## Live runtime status

For agents actually running right now (in-progress / completed / failed), this static roster does
**not** track that — use the live task list or the `/workflows` view instead. This file is the squad
overview and a place to jot the current assignment per agent.

_Last updated: 2026-06-26 10:02_
