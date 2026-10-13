# Portability and publication audit

Reviewed on 2026-10-13 against version 0.8.3.

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
Version 0.7.1 updates English documentation, dashboard examples and funding links;
it does not change metric collection or control behaviour. Code comments and
docstrings are in English; translated interface strings remain supported.
Version 0.8.0 changes authentication setup and renewal: separate browser/master
methods, automatic Android ID for browser tokens, fixed error categories,
lightweight account discovery and a retry step holding exchanged credentials
only for the open flow. Metric collection and Google controls retain their
behaviour. Stored entry data remains compatible with earlier versions.
Version 0.8.1 adds a localized return link from the map and diagnostics view.
Bundled-panel navigation retains the overview instance; manual cards can use
same-dashboard routes or an explicit local `overview_path`. Metric collection,
stored entries and Google controls are unchanged.
Version 0.8.2 correlates restart/test feedback with each target and button, adds
network/point action-status sensors, and polls pending Google operation status
every five seconds for at most ten minutes. Duplicate pending writes are blocked;
acceptance, reported execution, completion and uncertain delivery are distinct.
Version 0.8.3 fixes mesh requests by preparing the discovered primary server,
waiting for its readiness, then starting the selected client with the required
server query parameter. A single request tracks both stages; failed preparation,
uncertain writes and concurrent status readers cannot send duplicate client
tests. Runtime has no household-specific server or point IDs.
Tests use synthetic addresses and inline fixtures, with no external captures.
An explicit file-selection audit excludes credentials, deployment helpers,
inventories, screenshots, private backups and virtual environments.

## Verification

The clean repository passed **155 Python tests** using the isolated HA
2026.10.1 framework, and **27 JavaScript tests**. Coverage includes bucket
boundaries, missing data, scoped targets, registry spoof rejection, typed action
validation, permissions, operation handling, existing Shelly controls and
frontend state-update coalescing. The backend passed Ruff's F/E9 checks.
Operation feedback tests exercise actual HA button events, queued/sending/
accepted/running/completed sensor transitions, target isolation, unload
cancellation, ambiguous responses, write errors, expiry and out-of-order reads.
Authentication tests additionally cover copy/paste normalization, incomplete and
wrong-service tokens, Google account challenges/outages/rate limits, lightweight
network discovery, retry without repeating cookie exchange, duplicate accounts,
native options-to-reauth routing and preservation of three device records,
entity IDs, stored credentials on failure and polling options on success.
English/Portuguese setup translations have matching keys and password fields
never receive submitted values as defaults. These use dummy credentials and
simulated Google responses; the new Google login has not been exercised with a
real account or installed on the household HA.

The 0.6.1 telemetry/actions baseline was installed with backups and validated on real HA: both
entries loaded, existing entities and unrelated device IDs/names were preserved,
MAC/Shelly RSSI readings remained available, four served JS modules matched the
source, and network/client histories worked in an authenticated browser. A
point-light command with an unchanged value was read back and completed.

Google restart, benchmark, pause, priority and destructive actions were not
executed live during the original installation. A subsequent point restart was
confirmed through Google's completed operation and a recorded uptime reset.
Other requests and HA permissions are tested in isolation; their live support
remains untested until each action is used. Unverified
schemas and metrics not supplied by the observed API are listed in
[CAPABILITIES.md](CAPABILITIES.md). No claim covers every Google Home feature.

The manual archive contains runtime, generic docs and dashboard examples.
Archives/test caches are ignored by Git. Publication metadata and the owner-approved MIT licence are set: see [PUBLISHING.md](PUBLISHING.md).
The 0.7.0 panel's shared setup/reload, preservation of other panels and bundled
asset imports were tested in isolated real HA, alongside browser-side tab, locale
and update-coalescing tests. Version 0.8.0 was subsequently installed and checked
on real HA: existing entity/device IDs, user names and dashboard configuration
were preserved, both entries loaded, and the map and usage history rendered.
Uploading this clean copy does not publish private captures. Repository
visibility is public and the owner approved MIT. Release 0.7.0 is published;
0.7.1 packages the documentation and funding update separately.
Version 0.8.0 publishes the guided authentication flow and the English
[authentication guide](AUTHENTICATION.md).

The 0.8.3 mesh protocol was also checked against a real deployment: the initial
request was rejected, a server-qualified request without preparation failed at
the device, and preparing the primary first produced a completed operation with
a positive, newly dated saved result. Private captures are excluded. The added
[endpoint research](API_ENDPOINTS.md) distinguishes successful additional reads,
historical paths, unverified schemas and unusable local diagnostic responses.
