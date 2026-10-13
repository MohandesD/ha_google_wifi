"""Import transport/model without pretending to run Home Assistant."""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("gwi_test")
package.__path__ = [str(ROOT / "custom_components" / "google_wifi_insights")]
sys.modules["gwi_test"] = package
