import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).parent


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ['check_candidate.py', 'protected-skills.json']:
            shutil.copy2(BASE / name, self.root / name)
        self.installed = self.root / 'installed'
        self.installed.mkdir()
        (self.installed / 'SKILL.md').write_text('User-confirmed current wording\n')
        self.candidate = self.root / 'candidate'
        shutil.copytree(self.installed, self.candidate)
        self.before = (self.installed / 'SKILL.md').read_bytes()

    def tearDown(self):
        self.assertEqual(self.before, (self.installed / 'SKILL.md').read_bytes())
        self.tmp.cleanup()

    def run_guard(self):
        return subprocess.run([sys.executable, str(self.root / 'check_candidate.py'), '--skill', 'walmart-out-of-stock-copy', '--installed', str(self.installed), '--candidate', str(self.candidate)], capture_output=True).returncode

    def test_equal_noop(self):
        self.assertEqual(self.run_guard(), 0)

    def test_old_upstream_blocked(self):
        (self.candidate / 'SKILL.md').write_text('Old upstream wording\n')
        self.assertEqual(self.run_guard(), 3)

    def test_future_upstream_change_blocked(self):
        with (self.candidate / 'SKILL.md').open('a') as f:
            f.write('\nNew upstream revision\n')
        self.assertEqual(self.run_guard(), 3)

    def test_future_local_edit_stays_protected(self):
        with (self.installed / 'SKILL.md').open('a') as f:
            f.write('\nNew authorized local edit\n')
        self.before = (self.installed / 'SKILL.md').read_bytes()
        self.assertEqual(self.run_guard(), 3)

    def test_missing_policy_blocks(self):
        (self.root / 'protected-skills.json').unlink()
        self.assertEqual(self.run_guard(), 2)

    def test_corrupt_policy_blocks(self):
        (self.root / 'protected-skills.json').write_text('{}')
        self.assertEqual(self.run_guard(), 2)

    def test_missing_candidate_blocks(self):
        shutil.rmtree(self.candidate)
        self.assertEqual(self.run_guard(), 2)

if __name__ == '__main__':
    unittest.main()
