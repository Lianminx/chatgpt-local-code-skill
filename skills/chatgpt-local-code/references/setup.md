# Reproducible macOS setup

## Prerequisites and trust

Python 3.9+, Node.js 22+, npm, Git, an independently installed ngrok CLI, ngrok's free dev domain, and a ChatGPT account/workspace that can add custom MCP servers. A ChatGPT inference API key is not used by this route. Review third-party CodexPro code before running it with your user permissions.

The helper's default state is `~/.local/share/chatgpt-local-code`, outside the allowed source root. Each deployment supports one explicitly selected root. Do not select the home directory or `/`: these contain the required private state, so the helper rejects them. It does not edit the already-running custom Murphy installation.

```sh
python3 scripts/bridge.py install
python3 scripts/bridge.py configure --root /absolute/path/to/repo \
  --domain your-assigned-name.ngrok-free.dev --ngrok /absolute/path/to/ngrok \
  --confirm-public-access
```

`configure` asks for the ngrok authtoken using hidden input. Browser login alone does not authenticate the CLI. Reconfiguration preserves the MCP token. Public domain changes require updating the ChatGPT connector URL. Do not commit the state directory. The helper explicitly fixes writes/bash/transcript access off; there is no flag that grants them.

`install` checks out CodexPro `113472c6ff0a1516b6f223a43cd355abdf2e61ae` (0.30.3), uses the bundled dependency snapshot, makes the Zod 4 `z.record` signature adjustment, builds, audits production dependencies, and runs all upstream smoke groups. This is a local adaptation, not an upstream release or a general security certification. Package versions in the lock were tested on 2026-11-01. Reassess before deployment; newly disclosed vulnerabilities should block public startup until reviewed, patched and retested. Do not replace an existing runtime in place without preserving its state and obtaining scope approval.

## Test and run

```sh
# In terminal A (local listener only; no ngrok yet):
python3 scripts/bridge.py serve
# In terminal B:
python3 scripts/bridge.py verify
# After stopping terminal A, enable both services at macOS login:
python3 scripts/bridge.py enable-autostart --confirm-autostart
python3 scripts/bridge.py verify --public
python3 scripts/bridge.py status
```

The verifier creates one random harmless fixture directory inside the selected root and removes it in `finally`. It tests file reads, denied writes, secret patterns, parent/symlink escapes, authentication, disabled tools and blocked public management routes. Do not run if creating/removing that fixture is outside the authorized scope. The fixture is fake content, not a real credential. `--public` sends this fake fixture over ngrok.

The HTTPS credential-bearing address is in `<state>/connector-url.txt`, mode 0600. Put the whole URL into the custom MCP server form; choose No authentication for this query-token compatibility route. The public domain alone, without token, must return 401. Select the installed plugin using `@` and ask for a shallow listing. Never publish the full URL or real screenshots containing tokens.

```sh
python3 scripts/bridge.py stop       # unload this session; next login starts again
python3 scripts/bridge.py start      # load configured LaunchAgents again
python3 scripts/bridge.py disable-autostart  # unload and remove only this deployment's jobs
```

Login-time start requires a logged-in user, available home/project paths and internet. Sleep/offline makes it unreachable. Stop is not permanent disable. The domain is account-bound, not a domain you independently own; free quotas/terms can change.

## Failures worth distinguishing

- `ERR_NGROK_105`: wrong/malformed authtoken. Recopy the value, not the example command. Do not show it to the assistant.
- `ERR_NGROK_9009`: free agent inherited HTTP proxy mode. The provided launch config clears proxy variables for ngrok only. Do not change system networking.
- `ERR_NGROK_3200`: endpoint offline; inspect agent status before changing ChatGPT settings.
- 401 from MCP: missing/wrong MCP token, which is distinct from ngrok's account token.
- Port already used: inspect ownership; do not kill another service. Change ports in configure.
- CLI succeeds but ChatGPT fails: check account custom-plugin permission, full URL, installed plugin/tool refresh and selected conversation. Do not assume a specific model or entitlement.
- Cloudflare Quick Tunnels are temporary, not stable domain reservations. Cloudflare named public HTTP routing usually requires a domain on Cloudflare. Secure MCP Tunnel is a separate official alternative with its own setup, not a way to reuse the ngrok recipe unchanged.

## Sources (checked 2026-11-01)

- https://github.com/rebel0789/codexpro
- https://developers.openai.com/api/docs/guides/custom-mcp-server
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://ngrok.com/docs/pricing-limits/free-plan-limits/
- https://ngrok.com/docs/agent/config/v3/
- https://ngrok.com/docs/errors/err_ngrok_9009/
- https://developers.cloudflare.com/tunnel/get-started/
