"""Build a manual-install archive from an explicit, reviewed file allowlist."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
component = root / "custom_components/google_wifi_insights"
version = json.loads((component / "manifest.json").read_text(encoding="utf-8"))["version"]
files = sorted(p for p in component.rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".yaml", ".js") and "__pycache__" not in p.parts)
if (component / "LICENSE").is_file():
    files.append(component / "LICENSE")
files += sorted((root / "www").glob("*.js"))
files += [root / name for name in ("README.md", "INSTALL.md", "CONTRIBUTING.md", "CREDITS.md", "dashboard.yaml", "dashboard-map.yaml", "dashboard-overview.yaml")]
files += sorted((root / "docs").glob("*.md"))
if (root / "LICENSE").is_file():
    files.append(root / "LICENSE")
destination = root / "dist"
destination.mkdir(exist_ok=True)
archive = destination / f"google-wifi-insights-{version}-manual.zip"
with ZipFile(archive, "w", ZIP_DEFLATED) as output:
    for path in files:
        output.write(path, path.relative_to(root).as_posix())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(destination / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
print(json.dumps({"archive": str(archive), "files": len(files), "sha256": digest}))
