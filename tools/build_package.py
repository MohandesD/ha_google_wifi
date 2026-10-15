"""Build a reproducible manual archive from a reviewed public-file allowlist."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT_FILES = ("README.md", "INSTALL.md", "CONTRIBUTING.md", "CREDITS.md", "SECURITY.md", "SUPPORT.md", "CHANGELOG.md",
              "LICENSE", "dashboard.yaml", "dashboard-map.yaml", "dashboard-overview.yaml")
EXCLUDED_NAMES = {"secrets.yaml", "configuration.yaml", "automations.yaml", "scripts.yaml", "credentials.json"}
EXCLUDED_DIRS = {"__pycache__", ".storage", ".git", "node_modules", "evidence", "sources"}


def package_files(root):
    """Select only integration files, public assets and explicit documentation."""
    component = root / "custom_components/google_wifi_insights"
    files = [p for p in component.rglob("*") if p.is_file()
             and p.suffix in (".py", ".json", ".yaml", ".js", ".png", ".svg")
             and not EXCLUDED_DIRS.intersection(p.relative_to(root).parts)
             and p.name not in EXCLUDED_NAMES]
    if (component / "LICENSE").is_file():
        files.append(component / "LICENSE")
    files += list((root / "www").glob("*.js"))
    files += [root / name for name in ROOT_FILES if (root / name).is_file()]
    files += [p for p in (root / "docs").rglob("*") if p.is_file() and p.suffix in (".md", ".png", ".svg")]
    return sorted(set(files))


def source_bytes(path):
    """Keep public text byte-identical across Windows and Linux checkouts."""
    data = path.read_bytes()
    return data if path.suffix == ".png" else data.replace(b"\r\n", b"\n")


def build_package(root):
    component = root / "custom_components/google_wifi_insights"
    version = json.loads((component / "manifest.json").read_text(encoding="utf-8"))["version"]
    files = package_files(root)
    destination = root / "dist"
    destination.mkdir(exist_ok=True)
    archive = destination / f"google-wifi-insights-{version}-manual.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as output:
        for path in files:
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("Package source escapes the checkout")
            info = ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            output.writestr(info, source_bytes(path))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (destination / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return {"archive": str(archive), "files": len(files), "sha256": digest}


if __name__ == "__main__":
    print(json.dumps(build_package(Path(__file__).resolve().parents[1])))
