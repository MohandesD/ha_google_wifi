# Portability and publication audit

Reviewed on 2026-10-13 against version 0.7.0.

## Runtime and export

Selected runtime contains no household-specific point names, MAC addresses,
HA device/entry IDs, account emails or real tokens. Discovery obtains networks
and clients from the account and matches HA devices with current registry data.
Names are data, not hardcoded routing rules. Protocol URLs/scopes/signatures,
enums, size limits, RSSI display thresholds and retry timing are implementation
constants. The editable local gateway default is not a required address.
Polling and eligible Shelly roaming settings are configurable. Language and
time zone follow HA. An optional network_entity uses the user's own entity.

Metrics/actions retain the reviewed live 0.6.1 behaviour. Version 0.7.0 adds
automatic bundled frontend registration, real repository metadata, internal
map routing and cache versions. Examples remain generic.
Tests use synthetic addresses and inline fixtures, with no external captures.
An explicit file-selection audit excludes credentials, deployment helpers,
inventories, screenshots, private backups and virtual environments.

## Verification

The clean repository passed **93 Python tests**, including seven isolated HA
2026.10.1 framework tests, and **22 JavaScript tests**. Coverage includes bucket
boundaries, missing data, scoped targets, registry spoof rejection, typed action
validation, permissions, operation handling, existing Shelly controls and
frontend state-update coalescing. The backend passed Ruff's F/E9 checks.

The 0.6.1 telemetry/actions baseline was installed with backups and validated on real HA: both
entries loaded, existing entities and unrelated device IDs/names were preserved,
MAC/Shelly RSSI readings remained available, four served JS modules matched the
source, and network/client histories worked in an authenticated browser. A
point-light command with an unchanged value was read back and completed.

Google restart, benchmark, pause, priority and destructive actions were not
executed live during installation. Requests and HA permissions are tested in
isolation; live support remains untested until each action is used. Unverified
schemas and metrics not supplied by the observed API are listed in
[CAPABILITIES.md](CAPABILITIES.md). No claim covers every Google Home feature.

The manual archive contains runtime, generic docs and dashboard examples.
Archives/test caches are ignored by Git. Publication still requires real
repository metadata and a selected license: see [PUBLISHING.md](PUBLISHING.md).
The 0.7.0 panel's shared setup/reload, preservation of other panels and bundled
asset imports were tested in isolated real HA, alongside browser-side tab, locale
and update-coalescing tests. The running household HA has not been upgraded to
0.7.0. Uploading this clean copy does not publish private captures. Repository
visibility/licence remain an owner decision; no release has been published.
