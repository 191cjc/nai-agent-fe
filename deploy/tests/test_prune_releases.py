"""Destructive cleanup checks use only disposable synthetic release trees."""

import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "prune_releases.py"
SPEC = importlib.util.spec_from_file_location("prune_releases", SCRIPT)
prune = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prune
SPEC.loader.exec_module(prune)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = prune.Layout(Path(self.temporary.name))
        self.now = datetime(2035, 1, 1, tzinfo=UTC).timestamp()
        for root in (self.layout.api, self.layout.web, self.layout.assets):
            root.mkdir(parents=True)
        for root in (self.layout.api, self.layout.web):
            releases = [self.release(root, days) for days in (1, 2, 3)]
            (root.parent / "current").symlink_to(releases[0])

    def release(self, root, days):
        timestamp = self.now - days * prune.DAY
        name = datetime.fromtimestamp(timestamp, UTC).strftime("%Y%m%dT%H%M%SZ")
        path = root / (name + "-abcdef0")
        path.mkdir()
        if root == self.layout.web:
            (path / "assets").mkdir()
        os.utime(path, (timestamp, timestamp))
        return path

    def asset(self, name, days=500):
        path = self.layout.assets / name
        path.write_text("synthetic build asset")
        timestamp = self.now - days * prune.DAY
        os.utime(path, (timestamp, timestamp))
        return path

    def run_cleanup(self, apply=False, running=None, now=None):
        return prune.cleanup(
            self.layout, apply=apply, now=self.now if now is None else now,
            running_api=lambda: running,
        )

    def test_preview_then_apply_only_expired_releases(self):
        old_api = self.release(self.layout.api, 90)
        old_web = self.release(self.layout.web, 90)
        recent = self.release(self.layout.api, 20)
        unknown = self.layout.api / "operator-notes"
        unknown.mkdir()
        report = self.run_cleanup()
        self.assertEqual({item["path"] for item in report["candidates"]},
                         {str(old_api), str(old_web)})
        self.assertTrue(old_api.exists())
        self.assertTrue(old_web.exists())
        applied = self.run_cleanup(apply=True)
        self.assertEqual(set(applied["removed"]), {str(old_api), str(old_web)})
        self.assertFalse(old_api.exists())
        self.assertFalse(old_web.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(unknown.exists())
        self.assertEqual(self.run_cleanup(apply=True)["removed"], [])

    def test_current_and_running_api_survive_outside_newest_three(self):
        current = self.release(self.layout.api, 100)
        live = self.release(self.layout.api, 120)
        link = self.layout.api.parent / "current"
        link.unlink()
        link.symlink_to(current)
        self.run_cleanup(apply=True, running=live)
        self.assertTrue(current.exists())
        self.assertTrue(live.exists())
        self.assertEqual(len(list(self.layout.api.iterdir())), 5)

    def test_three_newest_remain_even_when_all_are_old(self):
        old_now = self.now + 400 * prune.DAY
        oldest = self.release(self.layout.api, 150)
        self.run_cleanup(apply=True, now=old_now)
        self.assertFalse(oldest.exists())
        self.assertEqual(len(list(self.layout.api.iterdir())), 3)

    def test_recent_copy_of_old_named_release_is_preserved(self):
        path = self.layout.api / "20200101T000000Z-abcdef0"
        path.mkdir()
        os.utime(path, (1, 1))
        self.run_cleanup(apply=True, now=time.time())
        self.assertTrue(path.exists())

    def test_assets_protect_lazy_members_and_cache_lifetime(self):
        kept = self.asset("lazy-AbCd1234.js")
        recent = self.asset("recent-AbCd1234.css", days=100)
        unknown = self.asset("operator-notes.txt")
        expired = self.asset("orphan-ZyXw9876.js")
        current = (self.layout.web.parent / "current").resolve()
        (current / "assets" / kept.name).write_text("synthetic lazy import")
        self.run_cleanup(apply=True)
        self.assertTrue(kept.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(unknown.exists())
        self.assertFalse(expired.exists())

    def test_missing_retained_asset_inventory_skips_shared_cleanup(self):
        (self.layout.web / "unfinished-build").mkdir()
        expired = self.asset("orphan-ZyXw9876.js")
        old = self.release(self.layout.api, 90)
        report = self.run_cleanup(apply=True)
        self.assertTrue(expired.exists())
        self.assertFalse(old.exists())
        self.assertEqual(len(report["warnings"]), 1)

    def test_recently_copied_old_asset_uses_ctime_guard(self):
        path = self.asset("orphan-ZyXw9876.js")
        os.utime(path, (1, 1))
        self.run_cleanup(apply=True, now=time.time())
        self.assertTrue(path.exists())

    def test_symlinked_retained_asset_skips_shared_cleanup(self):
        expired = self.asset("orphan-ZyXw9876.js")
        current = (self.layout.web.parent / "current").resolve()
        (current / "assets" / "lazy-AbCd1234.js").symlink_to(expired)
        report = self.run_cleanup(apply=True)
        self.assertTrue(expired.exists())
        self.assertTrue(report["warnings"])

    def test_unreadable_asset_walk_skips_shared_cleanup(self):
        expired = self.asset("orphan-ZyXw9876.js")

        def unreadable_walk(_root, *, followlinks, onerror):
            onerror(PermissionError("synthetic inaccessible inventory"))
            return iter(())

        with patch.object(prune.os, "walk", side_effect=unreadable_walk):
            report = self.run_cleanup(apply=True)
        self.assertTrue(expired.exists())
        self.assertTrue(report["warnings"])

    def test_current_escape_is_refused_before_deletion(self):
        old = self.release(self.layout.api, 90)
        link = self.layout.web.parent / "current"
        link.unlink()
        link.symlink_to(self.layout.prefix)
        with self.assertRaises(ValueError):
            self.run_cleanup(apply=True)
        self.assertTrue(old.exists())

    def test_symlink_root_is_refused(self):
        old = self.release(self.layout.api, 90)
        self.layout.assets.rmdir()
        self.layout.assets.symlink_to(self.layout.prefix, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_cleanup(apply=True)
        self.assertTrue(old.exists())

    def test_release_symlink_is_retained_and_embedded_link_never_followed(self):
        outside = self.layout.prefix / "synthetic-private-data"
        outside.mkdir()
        sentinel = outside / "keep.txt"
        sentinel.write_text("synthetic sentinel")
        link = self.layout.api / "20200101T000000Z-1234567"
        link.symlink_to(outside, target_is_directory=True)
        old = self.release(self.layout.api, 90)
        (old / "external").symlink_to(outside, target_is_directory=True)
        self.run_cleanup(apply=True)
        self.assertTrue(link.is_symlink())
        self.assertFalse(old.exists())
        self.assertEqual(sentinel.read_text(), "synthetic sentinel")

    def test_replaced_candidate_is_refused(self):
        old = self.release(self.layout.api, 90)
        candidate = next(item for item in prune.make_plan(self.layout, self.now, None).candidates
                         if item.path == old)
        moved = old.with_name("operator-kept")
        old.rename(moved)
        old.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(ValueError):
            prune.remove(candidate)
        self.assertTrue(moved.exists())

    def test_pointer_change_aborts_apply(self):
        old = self.release(self.layout.api, 90)
        calls = 0

        def changing_runtime():
            nonlocal calls
            calls += 1
            if calls == 2:
                link = self.layout.api.parent / "current"
                link.unlink()
                link.symlink_to(old)
            return None

        with self.assertRaises(ValueError):
            prune.cleanup(self.layout, apply=True, now=self.now, running_api=changing_runtime)
        self.assertTrue(old.exists())

    def test_relative_layout_and_traversal_are_refused(self):
        with self.assertRaises(ValueError):
            prune.make_plan(prune.Layout(Path(".")), self.now, None)
        with self.assertRaises(ValueError):
            prune.directory(self.layout.prefix / "..")

    def test_runtime_protection_uses_actual_cwd_and_refuses_unexpected_layout(self):
        live = self.release(self.layout.api, 90)
        with (
            patch.object(prune.subprocess, "run", return_value=SimpleNamespace(stdout="123\n")),
            patch.object(prune.os, "readlink", return_value=str(live / "apps/api")),
        ):
            self.assertEqual(prune.running_api_release(self.layout), live)
        with (
            patch.object(prune.subprocess, "run", return_value=SimpleNamespace(stdout="123\n")),
            patch.object(prune.os, "readlink", return_value="/unrelated/process"),
            self.assertRaises(ValueError),
        ):
            prune.running_api_release(self.layout)
        with patch.object(prune.subprocess, "run", return_value=SimpleNamespace(stdout="0\n")):
            self.assertIsNone(prune.running_api_release(self.layout))

    def test_runtime_inspection_error_refuses_cli_apply(self):
        old = self.release(self.layout.api, 90)
        with (
            patch.object(sys, "argv", [str(SCRIPT), "--apply"]),
            patch.object(prune, "Layout", return_value=self.layout),
            patch.object(prune, "LOCK", self.layout.prefix / "cleanup.lock"),
            patch.object(prune, "running_api_release", side_effect=subprocess.CalledProcessError(
                1, ["systemctl"],
            )),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(prune.main(), 1)
        self.assertTrue(old.exists())

    def test_lock_excludes_second_cleanup_and_rejects_symlink(self):
        lock = self.layout.prefix / "cleanup.lock"
        with prune.cleanup_lock(lock), self.assertRaises(BlockingIOError):
            with prune.cleanup_lock(lock):
                self.fail("second lock was acquired")
        with prune.cleanup_lock(lock):
            pass
        lock.unlink()
        lock.symlink_to(self.layout.prefix / "outside.lock")
        with self.assertRaises(OSError):
            with prune.cleanup_lock(lock):
                self.fail("symlink lock was followed")

    def test_cli_defaults_to_preview(self):
        old = self.release(self.layout.api, 90)
        output = io.StringIO()
        with (
            patch.object(sys, "argv", [str(SCRIPT)]),
            patch.object(prune, "Layout", return_value=self.layout),
            patch.object(prune, "LOCK", self.layout.prefix / "cleanup.lock"),
            patch.object(prune, "running_api_release", return_value=None),
            patch.object(prune.time, "time", return_value=self.now),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(prune.main(), 0)
        self.assertEqual(json.loads(output.getvalue())["mode"], "dry-run")
        self.assertTrue(old.exists())

    def test_lock_refuses_other_owner_writable_mode_and_multiple_links(self):
        lock = self.layout.prefix / "cleanup.lock"
        safe = {"st_mode": stat.S_IFREG | 0o600, "st_uid": os.geteuid(), "st_nlink": 1}
        for unsafe in ({"st_uid": os.geteuid() + 1}, {"st_mode": stat.S_IFREG | 0o620},
                       {"st_nlink": 2}):
            with (
                self.subTest(unsafe=unsafe),
                patch.object(prune.os, "fstat", return_value=SimpleNamespace(**(safe | unsafe))),
                self.assertRaises(ValueError),
            ):
                with prune.cleanup_lock(lock):
                    self.fail("unsafe lock was acquired")


if __name__ == "__main__":
    unittest.main()
