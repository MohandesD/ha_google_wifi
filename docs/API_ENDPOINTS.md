# LAN and cloud endpoint research

Investigated on 2026-10-13. Google Wifi uses an unofficial API; a historical
endpoint name is not proof that its request schema or firmware still supports it.
Live evidence remains private and contains no exported Google credentials.
The results below describe the tested deployment, not universal support.

## Mesh test correction in 0.8.3

The client request requires a server point:

```text
POST /v2/accesspoints/{clientApId}/meshSpeedTest?serverApId={primaryApId}
```

Omitting `serverApId` produced HTTP 400 `INVALID_ARGUMENT`. Providing it alone
allowed creation but the device operation failed; its saved throughput was a
negative failure value, not a speed. Preparing the primary point first with
`POST /v2/accesspoints/{primaryApId}/localSpeedTest` allowed the subsequent client
measurement to complete with a positive throughput and a new result timestamp.

The integration discovers the primary from Google's explicit `isGroupRoot`
field in the selected network. It prepares the measurement server, monitors
readiness, sends the client test once, follows the client's operation and refreshes
saved results. Both stages are one HA action. Server readiness is not mesh-test
completion. Missing or ambiguous primaries are rejected before sending commands.
Neither stage changes network settings or restarts a point.

Google describes the mesh benchmark as a measurement between the primary and
additional points. It is not a measurement of every physical intermediate hop.
See [Google's mesh-test guide](https://support.google.com/googlehome/answer/7620337?hl=en).

## Cloud: reads already collected

Base URL: `https://googlehomefoyer-pa.googleapis.com/v2/`.
These reads use the authenticated account inside HA.

| Endpoint | Information | Integration use |
| --- | --- | --- |
| `groups` | Networks, AP identity/role/firmware, network settings and feature support | Discovery and filtered telemetry |
| `groups/{groupId}/status` | AP online state and WAN connectivity | Live availability |
| `groups/{groupId}/stations` | Clients, explicit AP associations, names, addresses, band and radio capability | Client entities and map |
| `groups/{groupId}/realtimeMetrics` | Current traffic and Google quality ratings | Traffic and quality entities |
| `groups/{groupId}/speedTestResults` | Internet download/upload and timestamp | Saved WAN benchmark |
| `groups/{groupId}/meshSpeedTestResults` | Per-client-AP mesh throughput and timestamp | Saved mesh benchmark |
| `groups/{groupId}/wifiblasterSpeedTestResults` | Client throughput, tested AP and timestamp | Saved device benchmark |
| `groups/{groupId}/backhaulOfChildNodes` | Reported backhaul connection type | Backhaul telemetry |
| `groups/{groupId}/historicalUsage` | WAN/client byte buckets and peak traffic | Minute/hour/day history and rolling totals |
| `groups/{groupId}/insightCards` | Advice, links and supported server actions | Filtered insights |
| `operations/{operationId}` | Command state | Explicit action monitoring |
| `operations/{operationId}/sensitiveInfo` | Requested client MAC records | Bounded identity lookup following an explicit MAC lookup request |
| `groups/{groupId}/meshConfiguration` | Opaque configuration | Availability only; content is excluded |

The groups response already contains DHCP pools/reservations, DNS mode, IPv6 and
UPnP settings, guest-network status, family policies, preferred QoS support and
firmware update information. These non-credential fields are available through
`get_google_metrics`; `groups/{groupId}` adds no new measurements in the observed deployment and is
now cached for 15 minutes as supplemental group information. Passwords, tokens and opaque configuration stay excluded.

## Additional cloud reads investigated

| Endpoint | Observed result | Use in 0.9.0 |
| --- | --- | --- |
| `groups/{groupId}` | HTTP 200; duplicates group metadata already collected | Supplemental group information, cached for 15 minutes |
| `apSoftware/{version}/releaseNotes` | HTTP 200; version, title, description and HTML | Versioned plain-text notes in HA and the map; cached for six hours per queried version |
| `userPreferences` | HTTP 200; `optInFlow` in this account | Filtered account context, cached for one hour |
| `accesspoints/{apId}/hardwareBundleSetupInfo` | HTTP 200; empty object for the tested point | Filtered hardware information if supplied; cached for one day per point |
| `connectedhome/adapters` | HTTP 404 | Historical endpoint; no data obtained |
| `groups/{groupId}/stationSets/{stationSetId}/stationActivity` | HTTP 400, including a bounded date-range attempt | Schema remains unverified; not added to normal polling |

Other public inventories mention `appSoftware/{version}/clientTypes/{type}/status`
and `oobeflow`. They remain historical discovery leads, not validated network
metrics. Public Foyer home-graph RPC research describes smart-home device and structure
metadata. It has not been validated for Wifi radio metrics in this integration
and was not exercised here.

## LAN reads investigated

Use the discovered point address, not a household-specific constant.

| Endpoint | Observed result | Information / limitation |
| --- | --- | --- |
| `GET /api/v1/status` | HTTP 200 on all four local points in subsequent validation | Firmware/update channel/state/progress, uptime, role, WAN mode/lease/gateway, DNS and exposed link flags |
| `GET /api/v1/wan-configuration` | HTTP 200 on two models, HTTP 404 on another | WAN type; no additional performance counters |
| `GET /api/v1/developer-configuration` | HTTP 200 on the primary | API environment and firmware-update URL; useful for diagnostics |
| `GET /api/v1/welcome-mat` | HTTP 200 on the primary | Enabled flag and guest welcome text/photo/title; configuration information |
| `GET /api/v1/connected-devices` | HTTP 400 on the primary | Historical path; request requirements remain unverified |
| `GET /api/v1/diagnostic-report` | HTTP 404 on one model; timeouts on others; HTTP 500 on the primary with a 60-second allowance | No usable report obtained on this firmware |

Version 0.9.0 collects the four successful LAN reads above. Local status is cached
for 60 seconds and supplemental LAN reads for one hour. Existing local-mode
addresses anchor the current cloud network; cloud-only users can configure
a LAN gateway in the integration options. A duplicated online primary IP,
mismatched LAN role or returned address prevents association. Denials and
unsupported endpoints back off for six hours; failures retain their original
timestamps and are explicitly stale. No diagnostic-report polling or
provisioning calls are added.
Read availability varies by model, firmware and reachability; cloud online state
does not prove the stored IP currently responds to LAN HTTP requests.

Historical diagnostic-report parsers describe protobuf reports containing files,
command output and network information. A usable report could provide radio,
station, interface or queue counters depending on firmware. Such counters were
not obtained here. Raw reports can contain credentials and should not be exposed
as entity attributes or automatically exported. Any future parser should extract
an explicit metric allowlist inside HA with strict size/decompression limits.

Attestation, identity proof, setup, registration and join-group endpoints are
provisioning/security functions. They are not performance telemetry and were not
called. Setup, firmware-channel changes, support log uploads, reset and removal
actions were not used during this investigation.

## What this does not establish

The observed reads do not add airtime utilization, noise floor, retry counts,
channel occupancy, actual intermediate mesh routes or pairwise RSSI. Link
benchmarks measure throughput at a particular time; they do not establish radio
saturation by themselves. Existing Google ratings and device-reported RSSI remain
distinct measurements. The additional successful reads above are collected in 0.9.0. Failed and
unverified endpoints remain excluded from routine polling. See
[INFORMATION.md](INFORMATION.md) for the information views and diagnostic entities.

## Primary references

- [Google mesh-test description](https://support.google.com/googlehome/answer/7620337?hl=en)
- [Original Android endpoint inventory](https://github.com/olssonm/google-wifi-api/issues/6)
- [Node client's request/result definitions](https://github.com/JamesHawkinss/google-wifi-api-node/blob/master/index.js)
- [Foyer Python client](https://github.com/djtimca/googlewifi-api)
- [Original LAN endpoint investigation](https://github.com/olssonm/google-wifi-api)
- [Diagnostic protobuf schema and parser](https://github.com/bengalaviz/googlewifi/tree/master/diagnosticreport)
- [Foyer home-graph/local-device API research](https://rithvikvibhu.github.io/GHLocalApi/)

These sources are protocol leads. The live observations above take precedence
over historical examples when describing the tested deployment.
