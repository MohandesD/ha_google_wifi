"""Set actual GitHub publication metadata locally; no network calls or tokens."""

import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("repository", help="Actual GitHub owner/repository")
parser.add_argument("--codeowner", required=True, help="Maintainer's GitHub username")
args = parser.parse_args()
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", args.repository):
    parser.error("Expected a GitHub owner/repository")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.codeowner):
    parser.error("Expected a GitHub username without @")
if args.repository.startswith("OWNER/"):
    parser.error("Replace OWNER with the actual account or organization")
manifest_path = Path(__file__).resolve().parents[1] / "custom_components/google_wifi_insights/manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["documentation"] = "https://github.com/" + args.repository
manifest["issue_tracker"] = manifest["documentation"] + "/issues"
manifest["codeowners"] = ["@" + args.codeowner]
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("Updated local documentation, issue tracker and codeowner metadata.")
