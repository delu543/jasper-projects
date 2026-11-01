# Architecture and boundaries

## State ownership

- Each `--project` resolves to a real directory. `.project-observatory/project.json` is the sole editable source of truth for milestones and review history. `init` adds the directory to that checkout's local Git exclude.
- Git state and project structure are collected read only on the server. They are time stamped and never promoted into manual acceptance.
- Optional GitHub and Codex adapters are independent. Their failure sets a stale/error marker, retaining previous useful information when possible.
- The browser receives a project-scoped snapshot over localhost. Server-sent events notify visible browsers after a refresh. The browser fetches a fresh snapshot; editing a form does not disappear during a data refresh.

## Review rule

A checkpoint has a stable ID, a phase, an explicit state, owner, acceptance criterion and evidence references. The server serializes writes and atomically replaces the JSON file. An accepted code checkpoint stores the current Git SHA and requires a clean working tree. It becomes `needs_review` when SHA or dirty state changes. A decision checkpoint is stable across unrelated commits. This prevents Git activity or an unreviewed test log from manufacturing project progress.

## Local security

The HTTP server listens only on `127.0.0.1`, checks Host and Origin, requires a per-process token for writes, limits request body size and serves only four explicit static files. Text from project names, Git and Codex is inserted into the UI with `textContent`. No page or tool output is executed as a command. GitHub reads use `gh` only after a user enables them. The Codex adapter opens its local index with SQLite `mode=ro`, filters by exact project cwd or descendants and reads only a bounded tail of matching task logs. The adapter is optional because Codex's local index schema can change.

## Deliberate limits

- The starter checkpoints are a template. A project owner must define what acceptance actually means.
- Code changes invalidate current code acceptance conservatively. A reviewer can reaccept an unaffected item with its existing evidence after checking the impact.
- GitHub Actions status is a remote signal, not evidence that the local working tree passed or that a release reached users.
- The Codex adapter discovers windows by local cwd. Tasks opened in a detached worktree elsewhere need to be run from the selected project or manually reported. Logs are activity, not authoritative running process state.
- No automated test or provider call runs by default. This preserves user resources and avoids accidental writes to production systems.

## Sources and versions

The implementation uses Node.js >=20 standard `http` and browser `EventSource`; no external runtime UI library. Git based CLI installation follows the [npm install documentation](https://docs.npmjs.com/cli/install/). GitHub creation and publication follow [GitHub CLI documentation](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github). Source methods were verified 2026-09-29. No third-party code was copied into the repository.
