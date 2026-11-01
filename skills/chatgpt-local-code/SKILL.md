---
name: chatgpt-local-code
description: Connect ChatGPT web to explicitly chosen local code using CodexPro read-only MCP and a stable ngrok HTTPS endpoint. Use for setup, troubleshooting, verification, and macOS login-time startup; not for model routing, browser-cookie extraction, or granting code execution.
---

# ChatGPT Local Code

Use the existing setup when present; do not replace working services or rotate tokens merely to standardize them. The supplied helper supports macOS, Node.js 22+ and Python 3.9+. Other OSes require an adapted lifecycle, not a claim of support.

## Agree on the boundary

Identify the real directory the user wants exposed, the destination (ChatGPT via ngrok), and whether automatic login-time startup is wanted. Prefer one repository; a larger explicitly authorized workspace is allowed. Reading through MCP transmits code to cloud services. Pattern filters do not discover every secret; the server is not an OS sandbox. Never promise offline execution or zero provider-side retention.

Keep the runtime, ngrok configuration, access token, credential-bearing connector URL and logs outside all allowed roots. Do not read browser profiles or cookies. The user logs in to official ChatGPT/ngrok themselves. Ask them to enter ngrok's existing authtoken into the helper's hidden prompt, never into chat, command arguments or a checked-in file. Never rotate or create credentials unless separately requested.

## Prepare and connect

Read [setup.md](references/setup.md) for commands, dependency pinning, expected checks and failure handling. Use `scripts/bridge.py --help`; all paths are configurable. The helper installs a pinned upstream revision with a tested dependency lock and one Zod compatibility change, rather than silently installing latest upstream code. Inspect the audit result before any public startup. Do not use `npm audit fix --force` as an unattended repair.

Configure only with explicit authorization of the directory and public tunnel. The helper exposes no writes, shell tool, handoff/export or Codex transcripts. It forwards only `/mcp`, retains token authentication and keeps ngrok inspection disabled. Neither `readOnlyHint` nor tool descriptions are the actual security boundary: verify the configured server modes and registered tools.

Complete local verification before public verification. Never submit actual private code merely for a connectivity test: use a harmless fixture explicitly created for that purpose. The connector URL file contains a bearer-equivalent secret; show its private local path instead of printing it in chat. In ChatGPT the query-token compatibility route uses “No authentication” in the UI but the MCP server still checks the token. Prefer supported OAuth/header authentication for multi-user deployments; this helper is a single-user setup.

Refresh current official ChatGPT MCP documentation before giving exact UI steps; account/workspace restrictions may hide the entry. The user installs/selects their custom plugin and performs a minimal listing test. A CLI MCP pass is not proof of account-level ChatGPT use or model selection.

## Lifecycle and completion

`enable-autostart` adds per-user macOS LaunchAgents only after explicit authorization, not a pre-login daemon. Do not touch existing Codex model routing, system proxies, unrelated launch agents or paid plans. ngrok free agents may reject inherited HTTP proxies: isolate only that child process; if direct access fails, report it rather than changing global networking or upgrading billing.

Verify the public endpoint again after a service restart; the domain and MCP token should stay stable. State exactly whether local transport, public transport, actual ChatGPT interaction and machine reboot were tested. Report stop/disable commands and the private URL file. Stop after two identical authentication failures and ask the user to recopy the authtoken; never expose it for debugging. For other errors, preserve the working connection while diagnosing where possible.
