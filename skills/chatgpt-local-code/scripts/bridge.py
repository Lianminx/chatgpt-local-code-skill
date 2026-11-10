#!/usr/bin/env python3
"""Single-user read-only CodexPro deployment helper. Credentials never go to argv."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import secrets
import shutil
import subprocess
import sys
import tempfile

UPSTREAM = 'https://github.com/rebel0789/codexpro.git'
REVISION = '113472c6ff0a1516b6f223a43cd355abdf2e61ae'
ASSETS = Path(__file__).resolve().parents[1] / 'assets'
PROXY_KEYS = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')
RUNTIME_POLICY = 2


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def private_write(path, text):
    path.write_text(text, encoding='utf-8')
    path.chmod(0o600)


def state_path(value):
    return Path(value).expanduser().resolve()


def is_within(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_root(root, state):
    root = Path(root).expanduser().resolve(strict=True)
    state = Path(state).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Root must be a directory.')
    if is_within(Path.home().resolve(), root):
        raise ValueError('Select a specific project, not your home directory or a parent directory.')
    if is_within(state, root) or is_within(root, state) or is_within(ASSETS, root):
        raise ValueError('Private state and installed skill must be outside the allowed root.')
    return root


def validate_domain(domain):
    domain = domain.lower().removeprefix('https://').rstrip('/')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.ngrok-free\.(?:app|dev)', domain):
        raise ValueError('Supply the account-assigned ngrok-free.app or ngrok-free.dev hostname.')
    return domain


def validate_port(value):
    value = int(value)
    if not 1024 <= value <= 65535:
        raise ValueError('Port must be between 1024 and 65535.')
    return value


def read_settings(state):
    return json.loads((state / 'settings.json').read_text())


def labels(state):
    suffix = hashlib.sha256(str(state).encode()).hexdigest()[:12]
    return ['io.github.chatgpt-local-code.' + suffix + '.' + name for name in ('server', 'ngrok')]


def job_paths(state):
    return [Path.home() / 'Library/LaunchAgents' / (label + '.plist') for label in labels(state)]


def require_current_runtime(state):
    marker = state / 'installed.json'
    if not marker.is_file() or json.loads(marker.read_text()).get('policy') != RUNTIME_POLICY:
        raise ValueError('Install the current runtime first. For an older installation, see the upgrade instructions.')


def patch_runtime(runtime):
    for file, before, after in [
        ('server.ts', 'z.record(z.any())', 'z.record(z.string(), z.any())'),
        ('server.ts', '  if (!shouldRegisterTool(config, name)) return;',
         '  if (process.env.CODEXPRO_LOCAL_CODE_ONLY === "1" && !["tree", "search", "read"].includes(name)) return;\n'
         '  if (!shouldRegisterTool(config, name)) return;'),
        ('guard.ts', 'nocase: false', 'nocase: process.env.CODEXPRO_LOCAL_CODE_ONLY === "1"'),
        ('searchOps.ts', '        if (guard.isBlockedRelativePath(rel)) continue;',
         '        if (guard.isBlockedRelativePath(rel)) continue;\n'
         '        if (process.env.CODEXPRO_LOCAL_CODE_ONLY === "1") {\n'
         '          try { guard.resolve(workspace, rel); } catch { continue; }\n'
         '        }'),
    ]:
        source = runtime / 'src' / file
        content = source.read_text(encoding='utf-8')
        expected = 2 if file == 'guard.ts' else 1
        if content.count(before) != expected:
            raise ValueError('Pinned upstream patch context differs; stop and inspect.')
        source.write_text(content.replace(before, after), encoding='utf-8')


def install(state):
    if state.exists() and (not state.is_dir() or any(state.iterdir())):
        raise ValueError('Use a new or empty private state directory. See the upgrade instructions for existing installations.')
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    state.chmod(0o700)
    for command in ('git', 'node', 'npm'):
        if not shutil.which(command):
            raise ValueError('Missing executable: ' + command)
    major = int(subprocess.check_output(['node', '--version'], text=True).lstrip('v').split('.')[0])
    if major < 22:
        raise ValueError('Node.js 22+ required.')
    with tempfile.TemporaryDirectory(prefix='.install-', dir=state) as staging:
        runtime = Path(staging) / 'runtime'
        run(['git', '-c', 'http.version=HTTP/1.1', 'clone', '--no-checkout', UPSTREAM, runtime])
        run(['git', 'checkout', '--detach', REVISION], cwd=runtime)
        for source, target in [('runtime-package.json', 'package.json'), ('runtime-package-lock.json', 'package-lock.json')]:
            shutil.copyfile(ASSETS / source, runtime / target)
        patch_runtime(runtime)
        run(['npm', 'ci', '--ignore-scripts'], cwd=runtime)
        run(['npm', 'audit', '--omit=dev', '--audit-level=moderate'], cwd=runtime)
        run(['npm', 'run', 'build'], cwd=runtime)
        run(['npm', 'run', 'smoke'], cwd=runtime)
        runtime.rename(state / 'runtime')
    shutil.copyfile(ASSETS / 'server.mjs', state / 'server.mjs')
    shutil.copyfile(ASSETS / 'verify.mjs', state / 'verify.mjs')
    private_write(state / 'installed.json', json.dumps({'revision': REVISION, 'policy': RUNTIME_POLICY}) + '\n')
    print('Pinned runtime installed, audited, built and smoke-tested; not exposed yet.')


def configure(args, state):
    if not args.confirm_public_access:
        raise ValueError('Explicit --confirm-public-access is required after user authorization.')
    require_current_runtime(state)
    if sys.platform == 'darwin' and (any(p.exists() for p in job_paths(state)) or
                                     any(job_loaded(label) for label in labels(state))):
        raise ValueError('Run disable-autostart before reconfiguring, then enable-autostart again with the new settings.')
    root = validate_root(args.root, state)
    domain = validate_domain(args.domain)
    port, gateway = validate_port(args.port), validate_port(args.gateway_port)
    if port == gateway:
        raise ValueError('The two ports must differ.')
    ngrok = Path(args.ngrok).expanduser().resolve(strict=True)
    if not ngrok.is_file() or not os.access(ngrok, os.X_OK):
        raise ValueError('ngrok must be an executable file.')
    if not sys.stdin.isatty():
        raise ValueError('Run configure in an interactive terminal for hidden token input.')
    token = getpass.getpass('Paste ngrok authtoken (hidden): ').strip()
    if not token or not re.fullmatch(r'[A-Za-z0-9_]+', token):
        raise ValueError('Invalid token characters. Copy the value, not the command.')
    config = ('version: "3"\nagent:\n  authtoken: ' + json.dumps(token) + '\n'
              '  web_addr: false\n  inspect_db_size: -1\n'
              '  remote_management: false\n  update_check: false\n')
    private_write(state / 'ngrok.yml', config)
    clean_env = {k: v for k, v in os.environ.items() if k not in PROXY_KEYS}
    run([ngrok, 'config', 'check', '--config', state / 'ngrok.yml'], env=clean_env)
    settings = {'root': str(root), 'domain': domain, 'port': port, 'gatewayPort': gateway,
                'node': str(Path(shutil.which('node')).resolve()), 'ngrok': str(ngrok)}
    private_write(state / 'settings.json', json.dumps(settings, indent=2) + '\n')
    mcp = state / 'mcp-token'
    if not mcp.exists():
        private_write(mcp, secrets.token_hex(32))
    private_write(state / 'connector-url.txt', 'https://' + domain + '/mcp?codexpro_token=' + mcp.read_text().strip() + '\n')
    print('Configured root:', root)
    print('Private connector URL file:', state / 'connector-url.txt')


def job_loaded(label):
    return subprocess.run(['/bin/launchctl', 'print', f'gui/{os.getuid()}/{label}'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def launch_jobs(state):
    c = read_settings(state)
    env = {'HOME': str(Path.home()), 'PATH': os.environ.get('PATH', '/opt/homebrew/bin:/usr/bin:/bin')}
    commands = [[c['node'], str(state / 'server.mjs'), str(state)],
                [c['ngrok'], 'http', f'http://127.0.0.1:{c["gatewayPort"]}', '--url', 'https://' + c['domain'],
                 '--config', str(state / 'ngrok.yml'), '--inspect=false', '--log', 'stdout', '--log-format', 'json']]
    result = []
    for index, (label, command) in enumerate(zip(labels(state), commands)):
        process_env = dict(env)
        if index == 1:
            process_env.update({key: '' for key in PROXY_KEYS})
        result.append({'Label': label, 'ProgramArguments': command, 'EnvironmentVariables': process_env,
                       'WorkingDirectory': str(state), 'RunAtLoad': True, 'KeepAlive': True,
                       'ThrottleInterval': 15, 'ExitTimeOut': 10, 'ProcessType': 'Background', 'Umask': 63,
                       'StandardOutPath': str(state / ('server.log' if index == 0 else 'ngrok.log')),
                       'StandardErrorPath': str(state / ('server.log' if index == 0 else 'ngrok.log'))})
    return result


def lifecycle(action, args, state):
    if sys.platform != 'darwin':
        raise ValueError('LaunchAgent lifecycle is macOS-only.')
    paths = job_paths(state)
    if action == 'enable-autostart':
        if not args.confirm_autostart:
            raise ValueError('Explicit --confirm-autostart required after user authorization.')
        require_current_runtime(state)
        jobs = launch_jobs(state)
        if any(p.exists() for p in paths):
            raise ValueError('LaunchAgents exist; use start or disable before replacing.')
        for p, job in zip(paths, jobs):
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as f:
                plistlib.dump(job, f)
            p.chmod(0o600)
        action = 'start'
    if action in ('stop', 'disable-autostart'):
        for label in reversed(labels(state)):
            if job_loaded(label):
                run(['/bin/launchctl', 'bootout', f'gui/{os.getuid()}/{label}'])
        if action == 'disable-autostart':
            for p in paths:
                p.unlink(missing_ok=True)
        print('Stopped. ' + ('Autostart disabled.' if action == 'disable-autostart' else 'Next login starts again.'))
    elif action == 'start':
        require_current_runtime(state)
        if not all(p.exists() for p in paths):
            raise ValueError('Run enable-autostart first.')
        for label, p in zip(labels(state), paths):
            if not job_loaded(label):
                run(['/bin/launchctl', 'bootstrap', f'gui/{os.getuid()}', p])
        print('Jobs loaded. Run verify --public; loading alone is not a connectivity test.')
    elif action == 'status':
        for label in labels(state):
            print(label, 'loaded' if job_loaded(label) else 'not loaded')
        print('Private connector URL file:', state / 'connector-url.txt')


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', default='~/.local/share/chatgpt-local-code')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('install')
    c = sub.add_parser('configure')
    c.add_argument('--root', required=True)
    c.add_argument('--domain', required=True)
    c.add_argument('--ngrok', required=True)
    c.add_argument('--port', type=int, default=8787)
    c.add_argument('--gateway-port', type=int, default=8788)
    c.add_argument('--confirm-public-access', action='store_true')
    sub.add_parser('serve')
    v = sub.add_parser('verify')
    v.add_argument('--public', action='store_true')
    for name in ('enable-autostart', 'start', 'stop', 'status', 'disable-autostart'):
        s = sub.add_parser(name)
        if name == 'enable-autostart':
            s.add_argument('--confirm-autostart', action='store_true')
    args = p.parse_args()
    state = state_path(args.state)
    if args.command == 'install':
        install(state)
    elif args.command == 'configure':
        configure(args, state)
    elif args.command in ('serve', 'verify'):
        require_current_runtime(state)
        c = read_settings(state)
        name = 'server.mjs' if args.command == 'serve' else 'verify.mjs'
        extra = ['--public'] if args.command == 'verify' and args.public else []
        run([c['node'], state / name, state, *extra])
    else:
        lifecycle(args.command, args, state)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped.', file=sys.stderr)
        sys.exit(130)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
