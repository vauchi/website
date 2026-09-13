#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for content manifest building.

The manifest's checksums are what clients verify downloaded content
against, and its three-tier source resolution is what decides whether a
build ships fresh locales or none at all. GitLab is the only true
boundary here and is the only thing stubbed; every tier that can be
driven from the filesystem is.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scriptloader import load

builder = load("build-manifest.py")


class Workspace:
    """The sibling-repo layout build-manifest.py resolves against.

    `src_dir.parent.parent` is the workspace root, so a website/ level
    sits between the source directory and the sibling repos.
    """

    def __init__(self, test_case, *, themes=None, locales=None, networks=None):
        tmp = tempfile.TemporaryDirectory()
        test_case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.src_dir = self.root / "website" / "app-files-src"
        self.src_dir.mkdir(parents=True)
        # build_manifest creates this before calling the resolvers, which
        # mkdir their own subdirectory without parents=True.
        self.output_dir = self.root / "website" / "public" / "app-files"
        self.output_dir.mkdir(parents=True)

        if networks is not None:
            (self.src_dir / "networks.json").write_text(
                json.dumps(networks), encoding="utf-8"
            )
        if themes is not None:
            sibling = self.root / "themes"
            sibling.mkdir()
            (sibling / "themes.json").write_text(json.dumps(themes), encoding="utf-8")
        if locales is not None:
            sibling = self.root / "locales"
            sibling.mkdir()
            for name, payload in locales.items():
                (sibling / name).write_text(json.dumps(payload), encoding="utf-8")


class NetworkStub:
    """Stand in for the GitLab API, the one true boundary in this module."""

    def __init__(self, test_case, *, files=None, fetch_succeeds=False):
        self.files = files or []
        self.fetch_succeeds = fetch_succeeds
        self.fetch_calls = []
        # setattr/getattr rather than attribute syntax: the module is loaded
        # dynamically, so a checker cannot see its names.
        self.original_fetch = getattr(builder, "fetch_gitlab_file")
        self.original_list = getattr(builder, "list_gitlab_files")
        setattr(builder, "fetch_gitlab_file", self._fetch)
        setattr(builder, "list_gitlab_files", self._list)
        test_case.addCleanup(self._restore)

    def _fetch(self, project, file_path, dest, _ref="main"):
        self.fetch_calls.append((project, file_path))
        if self.fetch_succeeds:
            Path(dest).write_text('{"stubbed": true}', encoding="utf-8")
            return True
        return False

    def _list(self, _project, _path="", _ref="main"):
        return list(self.files)

    def _restore(self):
        setattr(builder, "fetch_gitlab_file", self.original_fetch)
        setattr(builder, "list_gitlab_files", self.original_list)


class Checksums(unittest.TestCase):
    def _file(self, content: bytes) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "blob"
        path.write_bytes(content)
        return path

    def test_the_checksum_is_the_sha256_of_the_bytes(self):
        content = b"vauchi content"

        checksum = builder.compute_checksum(self._file(content))

        self.assertEqual(checksum, f"sha256:{hashlib.sha256(content).hexdigest()}")

    def test_the_checksum_carries_its_algorithm_prefix(self):
        self.assertTrue(builder.compute_checksum(self._file(b"x")).startswith("sha256:"))

    def test_an_empty_file_hashes_to_the_known_empty_digest(self):
        self.assertEqual(
            builder.compute_checksum(self._file(b"")),
            "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_a_file_larger_than_the_read_chunk_hashes_correctly(self):
        """The reader chunks at 8192 bytes; a one-chunk file proves nothing."""
        content = bytes(range(256)) * 200  # 51200 bytes, many chunks

        self.assertEqual(
            builder.compute_checksum(self._file(content)),
            f"sha256:{hashlib.sha256(content).hexdigest()}",
        )

    def test_a_single_changed_byte_changes_the_checksum(self):
        one = builder.compute_checksum(self._file(b"vauchi content"))
        other = builder.compute_checksum(self._file(b"vauchi contenu"))

        self.assertNotEqual(one, other)


class ThemeResolution(unittest.TestCase):
    def test_a_sibling_repo_is_preferred_and_no_api_call_is_made(self):
        workspace = Workspace(self, themes=[{"id": "dark"}])
        network = NetworkStub(self)

        resolved = builder.resolve_themes(workspace.src_dir, workspace.output_dir)

        self.assertIsNotNone(resolved)
        self.assertEqual(json.loads(resolved.read_text()), [{"id": "dark"}])
        self.assertEqual(network.fetch_calls, [], "sibling tier must not hit GitLab")

    def test_the_committed_copy_is_used_when_the_api_is_unreachable(self):
        workspace = Workspace(self)
        NetworkStub(self, fetch_succeeds=False)
        committed = workspace.src_dir / "themes"
        committed.mkdir()
        (committed / "themes.json").write_text('[{"id":"committed"}]', encoding="utf-8")

        resolved = builder.resolve_themes(workspace.src_dir, workspace.output_dir)

        self.assertIsNotNone(resolved)
        self.assertEqual(json.loads(resolved.read_text()), [{"id": "committed"}])

    def test_the_api_is_used_when_there_is_no_sibling(self):
        workspace = Workspace(self)
        network = NetworkStub(self, fetch_succeeds=True)

        resolved = builder.resolve_themes(workspace.src_dir, workspace.output_dir)

        self.assertIsNotNone(resolved)
        self.assertEqual(network.fetch_calls, [("vauchi/themes", "themes.json")])

    def test_no_source_at_all_yields_nothing_and_leaves_no_empty_directory(self):
        workspace = Workspace(self)
        NetworkStub(self, fetch_succeeds=False)

        resolved = builder.resolve_themes(workspace.src_dir, workspace.output_dir)

        self.assertIsNone(resolved)
        self.assertFalse((workspace.output_dir / "themes").exists())


class LocaleResolution(unittest.TestCase):
    def test_a_sibling_repo_is_preferred_and_no_api_call_is_made(self):
        workspace = Workspace(
            self, locales={"en.json": {"a": "A"}, "de.json": {"a": "A"}}
        )
        network = NetworkStub(self)

        resolved = builder.resolve_locales(workspace.src_dir, workspace.output_dir)

        self.assertEqual(
            sorted(p.name for p in resolved.glob("*.json")), ["de.json", "en.json"]
        )
        self.assertEqual(network.fetch_calls, [])

    def test_the_schema_file_is_not_shipped_as_a_locale(self):
        workspace = Workspace(
            self,
            locales={"en.json": {"a": "A"}, "locales.schema.json": {"type": "object"}},
        )
        NetworkStub(self)

        resolved = builder.resolve_locales(workspace.src_dir, workspace.output_dir)

        self.assertEqual([p.name for p in resolved.glob("*.json")], ["en.json"])

    def test_the_api_is_used_when_there_is_no_sibling(self):
        workspace = Workspace(self)
        network = NetworkStub(
            self, files=["en.json", "de.json", "locales.schema.json"], fetch_succeeds=True
        )

        resolved = builder.resolve_locales(workspace.src_dir, workspace.output_dir)

        self.assertEqual(
            sorted(p.name for p in resolved.glob("*.json")), ["de.json", "en.json"]
        )
        self.assertNotIn(
            ("vauchi/locales", "locales.schema.json"), network.fetch_calls
        )

    def test_a_build_without_locale_data_is_refused_rather_than_shipped(self):
        """Guards 2026-06-11-locale-fork-divergence: a committed fallback
        silently deployed stale locales, so there is deliberately none."""
        workspace = Workspace(self)
        NetworkStub(self, files=[], fetch_succeeds=False)

        with self.assertRaises(SystemExit) as raised:
            builder.resolve_locales(workspace.src_dir, workspace.output_dir)

        self.assertIn("refusing to build without locale data", str(raised.exception))

    def test_an_api_listing_that_yields_no_fetches_is_also_refused(self):
        workspace = Workspace(self)
        NetworkStub(self, files=["en.json"], fetch_succeeds=False)

        with self.assertRaises(SystemExit):
            builder.resolve_locales(workspace.src_dir, workspace.output_dir)


class ManifestShape(unittest.TestCase):
    def build(self) -> dict:
        self.workspace = Workspace(
            self,
            networks={"networks": []},
            themes=[{"id": "dark"}],
            locales={"en.json": {"a": "A"}, "de.json": {"a": "B"}},
        )
        NetworkStub(self)
        return builder.build_manifest(
            self.workspace.src_dir,
            self.workspace.output_dir,
            "1.2.3",
            "https://cdn.example.invalid",
        )

    def test_the_manifest_records_its_schema_version_and_base_url(self):
        manifest = self.build()

        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["base_url"], "https://cdn.example.invalid")

    def test_generated_at_is_an_utc_timestamp(self):
        manifest = self.build()

        self.assertTrue(
            manifest["generated_at"].endswith("+00:00"),
            manifest["generated_at"],
        )

    def test_each_content_entry_carries_the_requested_version(self):
        manifest = self.build()

        for name, entry in manifest["content"].items():
            with self.subTest(content=name):
                self.assertEqual(entry["version"], "1.2.3")

    def test_networks_is_recorded_with_a_checksum_matching_the_copied_file(self):
        manifest = self.build()
        entry = manifest["content"]["networks"]

        copied = self.workspace.output_dir / "networks.json"
        self.assertEqual(entry["checksum"], builder.compute_checksum(copied))
        self.assertEqual(entry["size_bytes"], copied.stat().st_size)
        self.assertEqual(entry["path"], "networks.json")

    def test_every_locale_is_listed_with_its_own_checksum(self):
        manifest = self.build()
        files = manifest["content"]["locales"]["files"]

        self.assertEqual(sorted(files), ["de", "en"])
        self.assertNotEqual(files["en"]["checksum"], files["de"]["checksum"])
        for lang, entry in files.items():
            with self.subTest(lang=lang):
                copied = self.workspace.output_dir / "locales" / entry["path"]
                self.assertEqual(entry["checksum"], builder.compute_checksum(copied))

    def test_themes_is_recorded_under_its_published_path(self):
        manifest = self.build()

        self.assertEqual(manifest["content"]["themes"]["path"], "themes/themes.json")

    def test_absent_content_is_omitted_rather_than_recorded_as_empty(self):
        workspace = Workspace(self, themes=[{"id": "dark"}], locales={"en.json": {}})
        NetworkStub(self)

        manifest = builder.build_manifest(
            workspace.src_dir, workspace.output_dir, "1.0.0", "https://x.invalid"
        )

        self.assertNotIn("networks", manifest["content"])
        self.assertIn("themes", manifest["content"])


if __name__ == "__main__":
    unittest.main()
