# AI Tool Input Hygiene

AI coding tools send repository context to third-party APIs. This is how they work. Managing what they see is as important as reviewing what they produce. In a QA framework this matters doubly: the repo holds credentials for the system under test (SUT), test-environment endpoints, and sometimes captured request/response data.

## The Input / Output / Display Risk Model

| Risk | Question | Where addressed |
|------|----------|-----------------|
| **Input** | What data reaches the AI provider? | Context exclusion (below) |
| **Output** | Did the AI produce safe, correct code? | Test / quality / security review stages |
| **Display** | What credentials appear in the terminal? | Credential display safety (below) |

The review stages handle output risk. Input risk and display risk require the additional practices below.

## Context Exclusion

Ensure sensitive files never enter the AI tool's context window:

- **`.gitignore`** — AI tools generally respect this. Verify it covers: `.env*`, `*.pem`, `*.key`, `credentials.*`, `*.netrc`, and any directory holding real or captured test data (fixtures with PII, recorded sessions, HAR captures, screenshots/videos from test runs).
- **`.claudeignore`** / equivalent tool-specific exclusions — Mirror your `.gitignore` patterns and add anything sensitive that happens to be tracked in git (e.g., config with internal SUT URLs, proprietary test datasets, environment manifests).
- **Secrets in code** — The security review stage catches these before commit, but they are also input risk while you are working. Prefer environment variables and secret managers over any in-repo secret. Never paste a live SUT token into a test file, fixture, or spec.
- **Test artifacts** — Logs, traces, and HAR files from a real environment can embed bearer tokens, session cookies, and PII. Exclude artifact output directories from both git and the AI tool's context.

## Account Hygiene

- Use company-managed AI accounts with enterprise/team plans where available.
- Enterprise plans provide contractual guarantees against training on your data.
- Personal accounts on company repos offer no data governance — treat this as equivalent to sending code to an external service.

## Credential Display Safety

AI tools construct and execute shell commands on your behalf. When those commands involve authentication, credentials can appear in the terminal UI — in the command preview, in command output, or in shell history. This is a concern during demos, screensharing, pair programming, or recorded sessions.

**Where credentials become visible:**
- **Command preview**: AI tools show the full command before execution. A `curl -H "Authorization: Bearer <token>"` exposes the token in the UI.
- **Command output**: Some tools echo auth details in verbose or debug output.
- **Terminal scrollback**: Credentials persist in scroll history after the command finishes.
- **Shell history**: Commands with literal tokens get saved to `~/.bash_history` or `~/.zsh_history`.

**Prefer authentication methods that keep credentials out of commands:**

| Approach | Credential Visibility | Example |
|----------|----------------------|---------|
| MCP server with config-based auth | Not visible — auth in server config | Token in MCP config file, never in commands |
| CLI with built-in auth | Not visible — auth in config file | Token in `~/.config/`, not in commands |
| `curl` with `--netrc-file` | Not visible — auth in netrc file | Credentials in `~/.netrc`, not in command |
| Environment variable in command | **Visible if expanded** | `$TOKEN` may appear as a literal value in output |
| Literal token in command | **Fully visible** | Worst case — avoid this pattern |

**For demos and screensharing:**
- Use **dedicated demo credentials** with minimal scope (read-only, limited to a throwaway test environment).
- **Rotate tokens immediately after** any public demo or recording.
- **Clear terminal scrollback** before sharing screen.
- Use **pre-canned outputs** for sensitive operations — demonstrate the result, not the live execution.
- Prefer a **demo / synthetic-data environment** where credential exposure has no impact.
- If possible, **pre-approve commands** in the AI tool before the demo so sensitive operations don't need to be run live.

**Prompt before exposing credentials:**

When about to execute a command that would include a credential in plaintext (e.g., a token in a `curl` header, an API key as a CLI argument), **stop and ask the user before constructing the command**. Do not write the command first and then ask — the credential would already be visible in the terminal at that point.

- Describe what you intend to do and why it requires a credential (e.g., "I need to call the SUT's API to check a record's state. This would require passing your token as a header.").
- Give the user the chance to: approve, suggest a safer alternative (MCP server, authenticated CLI), or cancel.
- If the user approves credential-bearing commands for the session, do not prompt again for the same type of operation. Treat it as a session-level permission.

This ensures the user always has a chance to prevent credential exposure before it happens — particularly valuable during demos or screensharing where they may have forgotten the screen is shared.

## No Secrets in Logs

Test frameworks log liberally — request bodies, headers, response payloads, assertion diffs. Any of these can carry a live secret.

- **Mask at the logging boundary.** Redact known credential keys (`authorization`, `token`, `api_key`, `password`, `cookie`, `set-cookie`) before anything is written to a log, captured into a report, or printed to the terminal.
- **Never log a raw auth header or request body** that contains credentials. Log the request shape (method, path, status) instead of the full payload when the payload may carry secrets.
- **Keep credentials out of error messages and assertion failures.** A failed assertion that dumps the full request including its `Authorization` header leaks the token into CI output and screenshots.
- **Scrub captured artifacts.** HAR files, network logs, and recorded responses should be redacted (or excluded) before they are saved, attached to a report, or fed back to the AI tool.

## Day-to-Day Defaults

- Instruct the AI tool to reference environment variables rather than reading and embedding literal token values into commands.
- MCP servers are the safest pattern for tool integrations — auth is configured once in the server config and never appears in any command.
- Authenticated CLIs are the next safest — they read from their own config files.
- Avoid patterns where the AI reads a token from a file and interpolates it into a `curl` command.

## What This Doesn't Cover

Organizational decisions (repo classification tiers, internal AI gateways, VPC-hosted models) are infrastructure and governance concerns outside this guidance's scope. This policy covers what a developer can control directly.
