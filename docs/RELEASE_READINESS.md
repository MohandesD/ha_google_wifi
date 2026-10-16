# Readiness for 1.0

0.9.3 is a stabilization beta. A public repository, green CI and a version number
do not establish universal hardware compatibility or an independent security audit.
The target for 1.0 is a reliable, clearly bounded custom integration. It is not a
claim to reproduce every Google Home feature or become an official Google product.

## Engineering checks

| Check | Evidence and boundary |
| --- | --- |
| Partial-network isolation | Synthetic transport tests cover failure before/after a healthy network, 403/404/500, transport errors, malformed responses and recovery. |
| Authentication and throttling | Whole-session failures remain explicit; credentials are not echoed, provider challenges are distinguished and throttling is bounded. |
| HA lifecycle and upgrades | An isolated real HA exercises configuration, native reauthentication, preserved registry IDs/names, enabled diagnostic preferences, reload, unload and removal. |
| Read/write isolation | Stale targets reject new controls. Advanced/removal actions default to disabled and retain interactive administrator/name checks. |
| Diagnostic privacy | Tests use fictional secrets and identifiers in both keys and values. Raw telemetry and screenshots of real networks are outside the shareable diagnostics boundary. |
| Scale | Synthetic 100/300-client HA tests measure startup, refresh, Python allocations and state payload size, and ensure one client's traffic update does not rewrite unrelated clients. |
| Package and UI | Sources/bundled modules/version imports match. Tests cover missing data, unavailable scopes, history gaps, localization, disclosure state, scrolling and keyboard focus. |
| Release tooling | HACS, hassfest, static checks, measured branch coverage, dependency audits and an allowlisted, reproducible archive run in CI. |

Current test counts, coverage and scale measurements are recorded in each release
and its GitHub Actions artifacts. CI's 90% combined statement/branch floor is a
regression gate for this project, not a claimed HA Quality Scale certification.
Full config-flow coverage and higher overall coverage remain improvements for 1.0.

## Compatibility matrix

| Environment/model | Current evidence | Before a stable support claim |
| --- | --- | --- |
| HA Core 2026.10.1, Python 3.14 | Minimum isolated framework target. | Fresh installation/upgrade through actual HACS on an independent HA. |
| Latest released HA Core | CI upgrades HA/frontend independently of the minimum job. Initially the latest and minimum are both 2026.10.1. | Review each newly released version's CI result and disclose failures. |
| HA OS / Container | Runtime framework and distributable checks; no OS-wide installation is performed by tests. | Independent installation reports for the installation types we claim. |
| Google WiFi | Earlier versions were exercised on one private deployment; 0.9.3 has no new live hardware trial. | Record model/firmware, account access, map, history and supported safe controls on 0.9.3. |
| Nest WiFi / Nest WiFi Pro | Shared unofficial endpoint assumptions; no independent model validation recorded. | Test each claimed model/firmware separately, including absent fields. |
| OnHub or other legacy firmware | Unverified. | Keep unsupported/unverified until an explicit successful report exists. |
| Wired / wireless backhaul, guest clients, multiple networks | Synthetic fixtures and missing-data handling. | Record actual account/network variations without inferring physical mesh hops. |
| Shelly Gen2/3/4 local radio | Protocol fixtures and prior MAC-verified readings; authenticated RPC is not supported. | Record actual model/firmware compatibility for every additional claimed device. |

No installation type or model is guaranteed merely by this table. Absent RSSI,
airtime/noise/retries and intermediate mesh hops must remain unavailable. Radio
saturation cannot be established from client counts or throughput alone.

## Community trial still required

Recommended exit criteria, maintained by this project:

- Five to ten independent installations, including first-time onboarding and more
  than one model/firmware where those models will be advertised.
- Approximately fourteen days without unresolved crashes, account-wide failures
  caused by one network, lost registry IDs or unexpected network-control writes.
- Successful install, update, rollback, removal and credential-renewal reports.
- Measured Recorder/database impact on an independent lab installation. Python
  allocation/state-size measurements do not measure full HA RSS or database growth.
- Manual browser/Companion App checks on desktop and mobile with keyboard access,
  stale/missing data and long information sections.
- No unresolved high-severity dependency findings or security reports.
- Advertise only actions actually validated; group/insight/removal operations
  remain experimental unless separately validated in a disposable lab network.

Use [SUPPORT.md](../SUPPORT.md) and the bug-report template for redacted reports.
Do not test disruptive or destructive actions on a household lighting network.
These external observations are intentionally pending; automated fixtures are not
substitutes for independent users or long-running hardware measurements.

## Distribution

HACS custom-repository installation and an announcement inviting beta testers can
precede 1.0. Default-catalogue inclusion is a separate submission. The integration
ships its own original brand assets for modern HA/HACS; it does not depend on a
central Brands pull request. No official endorsement or Quality Scale tier is
claimed. Freeze new endpoints during stabilization unless a fix requires them.

The subsequent 0.10.0 beta adds local point/area mappings, associated-area sensors,
management UI and read-only name proposals. It introduces no new Google writes
and does not convert the 0.9.3 hardware evidence into a 1.0 compatibility claim.
The automatic rename request schema/read-back/undo gates in
[MANAGEMENT.md](MANAGEMENT.md) remain pending.
