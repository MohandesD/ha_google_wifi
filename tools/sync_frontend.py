"""Bundle the compatibility card sources inside the HACS integration directory."""

import argparse
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true", help="Fail instead of replacing mismatched copies")
args = parser.parse_args()
target = root / "custom_components/google_wifi_insights/frontend"
target.mkdir(exist_ok=True)
files = sorted((root / "www").glob("*.js"))
assert len(files) == 4, "Expected the map, overview, model and history modules"
for source in files:
    destination = target / source.name
    value = source.read_bytes()
    if args.check:
        if not destination.exists() or destination.read_bytes() != value:
            raise SystemExit(f"Bundled frontend differs: {source.name}")
    else:
        destination.write_bytes(value)
print("All four frontend modules are bundled inside custom_components")
