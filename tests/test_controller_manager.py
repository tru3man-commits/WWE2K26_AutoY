import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import controller_manager as cm


class FakeHid:
    def __init__(self, paths=(), cloak=False):
        self.paths = set(paths)
        self.enabled = cloak
        self.fail_unhide = False
        self.fail_hide = False
    def prepare(self): pass
    def hidden(self): return self.paths.copy()
    def cloak(self): return self.enabled
    def unhide(self, paths):
        if self.fail_unhide: raise RuntimeError('driver busy')
        self.paths.difference_update(paths)
    def call(self, *args):
        it = iter(args)
        for arg in it:
            if arg == '--dev-hide':
                self.paths.add(next(it))
                if self.fail_hide: raise RuntimeError('partial write')
            elif arg == '--cloak-on': self.enabled = True
            elif arg == '--cloak-off': self.enabled = False


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.profile = root / 'profile.json'
        self.journal = root / 'session.json'
        cm.atomic_json(self.profile, {'name':'Xbox', 'paths':['physical-hid', 'physical-parent']})
    def tearDown(self): self.temp.cleanup()
    def manager(self, hid): return cm.Manager(hid, self.profile, self.journal)

    def test_normal_session_preserves_other_devices(self):
        hid = FakeHid(['wheel'], True); manager = self.manager(hid)
        manager.begin(arm=False)
        self.assertEqual(hid.paths, {'wheel','physical-hid','physical-parent'})
        manager.stop()
        self.assertEqual(hid.paths, {'wheel'})
        self.assertTrue(hid.enabled)
        self.assertFalse(self.journal.exists())

    def test_previously_hidden_controller_is_released(self):
        hid = FakeHid(['physical-hid','physical-parent'], True)
        manager = self.manager(hid); manager.begin(arm=False); manager.stop()
        self.assertEqual(hid.paths, set())

    def test_initial_cloak_off_restored(self):
        hid = FakeHid(); manager = self.manager(hid)
        manager.begin(arm=False); self.assertTrue(hid.enabled)
        manager.stop(); self.assertFalse(hid.enabled)

    def test_partial_hide_failure_rolls_back(self):
        hid = FakeHid(['wheel'], True); hid.fail_hide = True
        with self.assertRaises(RuntimeError): self.manager(hid).begin(arm=False)
        self.assertEqual(hid.paths, {'wheel'})
        self.assertFalse(self.journal.exists())

    def test_failed_recovery_keeps_journal_for_retry(self):
        hid = FakeHid(); manager = self.manager(hid); manager.begin(arm=False)
        hid.fail_unhide = True
        with self.assertRaises(RuntimeError): manager.stop()
        self.assertTrue(self.journal.exists())
        hid.fail_unhide = False
        cm.restore(hid, self.journal)
        self.assertFalse(self.journal.exists()); self.assertEqual(hid.paths, set())

    def test_old_watchdog_cannot_restore_new_session(self):
        hid = FakeHid(); manager = self.manager(hid); manager.begin(arm=False)
        cm.restore(hid, self.journal, token='expired-token')
        self.assertIn('physical-hid', hid.paths)
        self.assertTrue(self.journal.exists())

    def test_external_new_hide_is_not_disabled(self):
        hid = FakeHid(); manager = self.manager(hid); manager.begin(arm=False)
        hid.paths.add('another-app-controller')
        manager.stop()
        self.assertEqual(hid.paths, {'another-app-controller'})
        self.assertTrue(hid.enabled)

    def test_watchdog_failure_prevents_hiding(self):
        hid = FakeHid(); manager = self.manager(hid)
        with patch.object(cm, 'install_login_recovery'), patch.object(manager, 'arm_watchdog', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError): manager.begin()
        self.assertEqual(hid.paths, set()); self.assertFalse(self.journal.exists())

    def test_switch_profile_releases_previous_controller(self):
        hid = FakeHid(['physical-hid','physical-parent','wheel'], True)
        manager = self.manager(hid)
        manager.select({'name':'Other Xbox', 'paths':['other-xbox']})
        self.assertEqual(hid.paths, {'wheel'})
        self.assertEqual(manager.profile()['paths'], ['other-xbox'])

    def test_crash_recovery_is_idempotent(self):
        hid = FakeHid(); self.manager(hid).begin(arm=False)
        cm.restore(hid, self.journal); cm.restore(hid, self.journal)
        self.assertEqual(hid.paths, set()); self.assertFalse(hid.enabled)

    def test_unicode_and_spaces_roundtrip_in_profile(self):
        cm.atomic_json(self.profile, {'name':'Xbox - Richárd', 'paths':['HID\\VID_045E&PID_1234\\test']})
        self.assertEqual(cm.read_json(self.profile)['name'], 'Xbox - Richárd')

if __name__ == '__main__': unittest.main()
