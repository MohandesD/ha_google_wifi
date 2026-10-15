"""Check the distributable, synchronized versions and public credential hygiene."""

import hashlib
import json
import re
import runpy
from pathlib import Path
from zipfile import ZipFile


def key_paths(value, prefix=""):
    if not isinstance(value, dict):
        return {prefix}
    return {path for key, child in value.items() for path in key_paths(child, prefix + "." + key)}


def validate(root):
    component = root / "custom_components/google_wifi_insights"
    manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    for name in ("package.json", "package-lock.json"):
        package = json.loads((root / name).read_text(encoding="utf-8"))
        assert package["version"] == version, f"{name} version differs from manifest"
        if name == "package-lock.json":
            assert package["packages"][""]["version"] == version
    assert f'FRONTEND_VERSION = "{version}"' in (component / "frontend.py").read_text(encoding="utf-8")
    for source in (root / "www").glob("*.js"):
        assert source.read_bytes() == (component / "frontend" / source.name).read_bytes(), f"Stale bundled module: {source.name}"
    for module in (component / "frontend").glob("*.js"):
        assert all(value == version for value in re.findall(r'\?v=([^\s\"\']+)', module.read_text(encoding="utf-8"))), f"Stale imports: {module.name}"
    source = json.loads((component / "strings.json").read_text(encoding="utf-8"))
    assert source == json.loads((component / "translations/en.json").read_text(encoding="utf-8"))
    assert key_paths(source) == key_paths(json.loads((component / "translations/pt.json").read_text(encoding="utf-8"))), "Translation key mismatch"
    helpers = runpy.run_path(str(root / "tools/build_package.py"))
    expected = {path.relative_to(root).as_posix(): path for path in helpers["package_files"](root)}
    archive = root / "dist" / f"google-wifi-insights-{version}-manual.zip"
    patterns = [rb"(?:aas_et/|oauth2rt_1/|oauth2_4/)[A-Za-z0-9_./+=-]{40,}",
                rb"eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
                rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"]
    with ZipFile(archive) as packaged:
        names = packaged.namelist()
        assert len(names) == len(set(names)) and set(names) == set(expected), "Unexpected package member"
        for name in names:
            assert not name.startswith("/") and ".." not in Path(name).parts
            data = packaged.read(name)
            assert data == helpers["source_bytes"](expected[name]), f"Archive differs from source: {name}"
            if not name.endswith(".png"):
                assert not any(re.search(pattern, data) for pattern in patterns), f"Credential-like content in {name}"
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert (root / "dist/SHA256SUMS").read_text(encoding="utf-8").strip() == f"{digest}  {archive.name}"
    return {"version": version, "files": len(expected), "sha256": digest, "credential_findings": 0,
            "frontend_synchronized": True, "translations_synchronized": True}


if __name__ == "__main__":
    print(json.dumps(validate(Path(__file__).resolve().parents[1]), indent=2))
