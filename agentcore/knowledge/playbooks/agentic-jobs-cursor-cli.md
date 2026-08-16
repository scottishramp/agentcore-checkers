# Playbook: Creating Agentic Jobs with Cursor CLI

How AgentCore runs LLM ("agentic") work inside scheduled GitHub Actions jobs, and the recipe for
creating a new agentic job when Brian asks for one. Derived from the working daily runner
(`.github/workflows/agent-runner.yml`).

## The proven pattern (from the daily runner)

The daily `AgentCore Async Runner` workflow (cron 13:30 UTC + `workflow_dispatch` +
after `AgentCore Email Sync`) runs Cursor Agent CLI headless on an `ubuntu-latest` runner.

### 1. Install the CLI (once per job, BEFORE any step that needs it)

```yaml
- name: Install Cursor CLI
  run: |
    curl https://cursor.com/install -fsS | bash
    echo "$HOME/.cursor/bin" >> "$GITHUB_PATH"
```

`GITHUB_PATH` only affects *subsequent* steps. Order matters: the install step must come before
every consumer (this bit us when the school digest ran before the install step).

### 2. Authenticate

- CI: `CURSOR_API_KEY` repo secret, passed as env to the step that invokes the CLI.
- Local: `cursor-agent login` (browser flow) or `CURSOR_API_KEY` env. The local CLI lives at
  `~/.local/bin/cursor-agent`; `PATH` may not include it, so scripts should also probe
  `~/.local/bin` and `~/.cursor/bin` (see `find_cursor_cli()` in `scripts/email/email_evaluator.py`).

### 3. Invoke headless (print mode)

```bash
cursor-agent -p --output-format text --trust --model "$MODEL" "$PROMPT"
# fallback binaries, in order: cursor-agent, agent, `cursor agent`
```

- `-p` = non-interactive print mode: runs the prompt, prints the final answer, exits.
- `--trust` skips the workspace-trust prompt (required in CI, harmless locally).
- `--workspace .` optionally pins the workspace (used by the task adapter so the agent can edit
  the repo).
- Model comes from `AGENTCORE_CURSOR_MODEL` secret, default `grok-4.5`.
- Wrap in `subprocess.run(..., timeout=...)`; the runner uses 900–1200 s
  (`AGENTCORE_TASK_RUN_TIMEOUT_SECONDS`, `AGENTCORE_CURSOR_TIMEOUT_SECONDS`).

### 4. Two invocation styles in this repo

| Style | Example | Use when |
|---|---|---|
| Full agent with repo write access | `scripts/agent/run_cursor_task.py` (task adapter) | Brian's queued email/Chat/Telegram tasks; agent may edit the repo, runner commits after |
| Structured LLM call (JSON in → JSON out) | `scripts/email/email_evaluator.py` | Classification/evaluation inside a pipeline; prompt says "answer with ONLY the JSON array", caller parses and validates |

For structured calls: batch inputs (12/batch for email), strip code fences before `json.loads`,
retry once on parse failure, normalize/clamp every field, and keep a deterministic fallback so the
pipeline still completes if the LLM is unavailable.

### 5. Commit results

Runner steps commit artifacts with the bot identity and rebase-pull before push:

```bash
python3 scripts/agent/ensure_no_conflict_markers.py
git add <specific files>
git -c user.name="AgentCore Bot" -c user.email="scottishramp@gmail.com" commit -m "..."
git -c rebase.autoStash=true pull --rebase origin main
git push
```

Use `continue-on-error: true` on persist steps so a push race never fails the whole job.

## Recipe: new agentic job from a Brian ask

1. **Decide the trigger**: cron in an existing workflow (prefer adding a step to
   `agent-runner.yml` if the cadence matches its daily run), a new workflow with its own
   `schedule` + `workflow_dispatch`, or `workflow_run` chaining.
2. **Decide the invocation style** (table above). Structured JSON calls for pipelines; full agent
   via the task-adapter pattern when the job must reason over the repo or edit it.
3. **Write the script** under `scripts/`, with:
   - env/secret-driven config, no hardcoded credentials;
   - an idempotency ledger if the job processes items (pattern:
     `agentcore/knowledge/email/eval-ledger.json` — id → verdict + `evaluated_at`, pruned by age);
   - a cheap prefilter so the LLM only sees items worth evaluating;
   - a deterministic fallback path.
4. **Wire the workflow step(s)**: CLI install first, `CURSOR_API_KEY` + model env on the step,
   a persist step for any committed artifacts.
5. **Test**: run the script locally (fallback path at minimum), then `gh workflow run` and watch
   the run with `gh run watch`.
6. **Document**: architecture page (workflows/data stores), a playbook if the job has operating
   procedures, `agentcore/log.md` entry, hot-cache.

## Secrets available in Actions (relevant here)

`CURSOR_API_KEY`, `AGENTCORE_CURSOR_MODEL`, `AGENTCORE_GMAIL_*` (AgentCore mailbox OAuth),
`AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_JSON` (Brian mailbox OAuth), `TELEGRAM_BOT_TOKEN`,
`KV_REST_API_*` (Upstash), `VERCEL_TOKEN`. `GEMINI_API_KEY` is wired in the digest step as an
optional fast backend but is NOT yet set as a repo secret (see blockers).

## Gotchas

- Local `cursor-agent` on Brian's Mac is not logged in; CI is the reliable execution
  environment. Don't burn time on the local login TUI — it needs a real interactive terminal.
- `cursor-agent` prints prose around answers occasionally; structured callers must extract the
  JSON array (`find("[")` … `rfind("]")`) rather than parsing raw stdout.
- Print-mode output goes to stdout; CLI errors (auth, model slug) land on stderr with non-zero
  exit — surface `proc.stderr` in the raised exception for debuggability.
