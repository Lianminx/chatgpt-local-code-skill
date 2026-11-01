import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

MODULE = Path(__file__).resolve().parents[1] / 'skills/chatgpt-local-code/scripts/bridge.py'
spec = importlib.util.spec_from_file_location('bridge', MODULE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def test_reject_state_under_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError):
                bridge.validate_root(root, root / 'private')

    def test_accept_separate_state(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'repo'
            root.mkdir()
            self.assertEqual(bridge.validate_root(root, Path(d) / 'state'), root.resolve())

    def test_reject_symlink_root_containing_state(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / 'root'
            root.mkdir()
            link = base / 'link'
            link.symlink_to(root)
            with self.assertRaises(ValueError):
                bridge.validate_root(link, root / 'private')

    def test_domain(self):
        self.assertEqual(bridge.validate_domain('https://example.ngrok-free.dev/'), 'example.ngrok-free.dev')
        for domain in ['example.com', 'a.ngrok-free.dev@evil.com', 'a.ngrok-free.dev/path', 'bad host.ngrok-free.app']:
            with self.assertRaises(ValueError):
                bridge.validate_domain(domain)

    def test_ports(self):
        for port in [0, 80, 65536]:
            with self.assertRaises(ValueError):
                bridge.validate_port(port)
        self.assertEqual(bridge.validate_port(8787), 8787)

    def test_launch_jobs_have_no_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d)
            settings = {'root':'/tmp/example', 'domain':'example.ngrok-free.dev', 'port':8787,
                        'gatewayPort':8788, 'node':'/usr/bin/node', 'ngrok':'/usr/bin/ngrok'}
            (state/'settings.json').write_text(json.dumps(settings))
            jobs = bridge.launch_jobs(state)
            self.assertEqual(len(jobs), 2)
            self.assertIn('--inspect=false', jobs[1]['ProgramArguments'])
            self.assertNotIn('--authtoken', jobs[1]['ProgramArguments'])
            for key in bridge.PROXY_KEYS:
                self.assertEqual(jobs[1]['EnvironmentVariables'][key], '')
            self.assertTrue(all(j['RunAtLoad'] and j['KeepAlive'] for j in jobs))
            self.assertNotEqual(bridge.labels(state), bridge.labels(state/'other'))

    def test_private_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'secret'
            bridge.private_write(p,'fixture')
            self.assertEqual(p.stat().st_mode & 0o777,0o600)


if __name__ == '__main__':
    unittest.main()
