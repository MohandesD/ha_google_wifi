"""Exercise release packaging against disposable public and private fixtures."""

import json
import os
import runpy
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = runpy.run_path(str(ROOT / "tools/build_package.py"))
VALIDATE = runpy.run_path(str(ROOT / "tools/validate_release.py"))["validate"]


@pytest.fixture
def public_tree(tmp_path):
    """Create the minimal synchronized release tree without copying real data."""
    component = tmp_path / "custom_components/google_wifi_insights"
    (component / "frontend").mkdir(parents=True)
    (component / "translations").mkdir()
    (tmp_path / "www").mkdir()
    (tmp_path / "tools").mkdir()
    for name in ("build_package.py",):
        shutil.copyfile(ROOT / "tools" / name, tmp_path / "tools" / name)
    (component / "manifest.json").write_text('{"version":"0.9.3"}', encoding="utf-8")
    (component / "frontend.py").write_text('FRONTEND_VERSION = "0.9.3"\n', encoding="utf-8")
    for folder in (tmp_path / "www", component / "frontend"):
        (folder / "map.js").write_text('import "./other.js?v=0.9.3";\n', encoding="utf-8")
    for name in ("strings.json", "translations/en.json", "translations/pt.json"):
        (component / name).write_text('{"config":{"title":"Example"}}', encoding="utf-8")
    for name in ("package.json", "package-lock.json"):
        (tmp_path / name).write_text(json.dumps({"version": "0.9.3", "packages": {"": {"version": "0.9.3"}}}), encoding="utf-8")
    (tmp_path / "README.md").write_bytes(b"Public example\r\n")
    return tmp_path


def test_package_is_reproducible_and_excludes_private_files(public_tree):
    component = public_tree / "custom_components/google_wifi_insights"
    for name in ("secrets.yaml", "configuration.yaml", "credentials.json"):
        (component / name).write_text("private fixture", encoding="utf-8")
    for folder in (".storage", "evidence", "sources"):
        (component / folder).mkdir()
        (component / folder / "secret.json").write_text("private fixture", encoding="utf-8")
    (public_tree / "house-backup.json").write_text("private fixture", encoding="utf-8")
    first = BUILD["build_package"](public_tree)
    original = Path(first["archive"]).read_bytes()
    (public_tree / "README.md").write_bytes(b"Public example\n")
    os.utime(public_tree / "README.md", (1900000000, 1900000000))
    second = BUILD["build_package"](public_tree)
    assert Path(second["archive"]).read_bytes() == original
    assert first["sha256"] == second["sha256"]
    with ZipFile(first["archive"]) as archive:
        assert not any("private fixture" in archive.read(name).decode() for name in archive.namelist())
    assert VALIDATE(public_tree)["credential_findings"] == 0


@pytest.mark.parametrize("failure", ["version", "bundle", "translation", "credential", "archive", "checksum"])
def test_release_validation_rejects_invalid_distribution(public_tree, failure):
    BUILD["build_package"](public_tree)
    component = public_tree / "custom_components/google_wifi_insights"
    if failure == "version":
        (public_tree / "package.json").write_text('{"version":"0.9.2"}', encoding="utf-8")
    elif failure == "bundle":
        (component / "frontend/map.js").write_text("stale", encoding="utf-8")
    elif failure == "translation":
        (component / "translations/pt.json").write_text("{}", encoding="utf-8")
    elif failure == "credential":
        # A fabricated, nonfunctional token shape must still fail the public audit.
        (public_tree / "README.md").write_text("aas_et/" + "x" * 50, encoding="utf-8")
        BUILD["build_package"](public_tree)
    elif failure == "archive":
        (public_tree / "README.md").write_text("changed after packaging", encoding="utf-8")
    elif failure == "checksum":
        (public_tree / "dist/SHA256SUMS").write_text("incorrect", encoding="utf-8")
    with pytest.raises(AssertionError):
        VALIDATE(public_tree)
