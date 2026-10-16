# Validation and publication audit

Current engineering scope: 0.11.1 one-time name batches, reviewed on 2026-10-16. See the
[release checks](TESTING.md), [readiness matrix](RELEASE_READINESS.md) and
[GitHub Actions](https://github.com/spkon/ha_google_wifi/actions) for current evidence.

The 0.11.1 local suite passed 310 Python tests at 91.19% combined statement/branch
coverage and 69 frontend tests. New cases cover exact selection/confirmation,
sequential dispatch, changed previews, wrong network/client responses, rejected
or uncertain results, stop/navigation behavior, permission/network loss and
unchanged automatic-naming settings. The fictional browser demo also exercised
selection, confirmation and completion. Its local simulated completion is not
evidence of a real Google backend accepting a rename. Backend naming services
and device/entity identity behavior are unchanged in this patch.

## Isolation and privacy

The public package contains integration code, bundled UI, original brand assets,
generic dashboard examples and English documentation. Household configuration,
lighting automations, deployment helpers, captures, credentials and backups are
outside this repository and the manual package allowlist. Synthetic tests require
no real account, token, browser storage or LAN device.

Network discovery and HA matching use account/registry data, not household names
or hardcoded device IDs. Default gateway addresses, protocol URLs/signatures,
measurement thresholds and bounded retry limits are implementation constants.
Identity matching preserves other integrations and user-assigned device names.

0.9.3 removes AP IDs from diagnostics' hardware cache keys and hexadecimal IDs
from radio schema keys. Tests inject fictional credentials and identities into
keys and values. Raw network information and `get_google_metrics` remain private
data and must not be attached to public issues. See [SECURITY.md](../SECURITY.md).

## Automated behavior checks

Per-network failure tests cover inaccessible networks in either order, changed
schemas, total outages, recovery, global authentication/rate limits and task
cancellation. An isolated real HA confirms unavailable states, stable map routing,
write rejection, unchanged registry IDs and enabled preferences across reload.
Provider point names/firmware update without replacing user-assigned names.

Control tests cover registry spoof rejection, administrator permissions,
experimental/removal opt-ins, exact name confirmations, typed requests and
unconfirmed writes. Physical network removal/group changes are not executed.
RPC tests use loopback servers to check physical identity, narrow roaming writes,
oversized/invalid responses, provider errors and secret-safe failures.

Python tests measure combined statement/branch coverage with a 90% CI floor.
Synthetic 100/300-client tests produce aggregate allocation/timing/state-size
evidence and verify that one client's traffic change does not rewrite unrelated
clients. These are not Recorder/database-growth or complete HA process-memory tests.
Frontend tests cover unavailable network scopes, missing samples, localization,
operation feedback, history, disclosure behavior, scroll/focus and bundled routing.

CI includes minimum/latest released HA, Ruff, HACS, hassfest, dependency audits,
bundled module/version checks and reproducible public archive verification.
The package verifier detects common credential patterns and unexpected files;
it cannot prove that arbitrary personal data is absent. Release diffs require review.

## Live evidence boundary

Earlier versions were checked on a single private installation: entity/device
preservation, map/history rendering, measured Shelly signal, operation feedback
and a prepared mesh test informed the implementation. That history is not an
independent model compatibility matrix.

The 0.9.3 preparation does not access, install on, alter or restart that household
HA. Authentication with new real accounts, independent HACS installation, physical
Google/Nest models and a prolonged community trial remain pending in the
[1.0 checklist](RELEASE_READINESS.md). No Quality Scale tier or security certification
is claimed.
