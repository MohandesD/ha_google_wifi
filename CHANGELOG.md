# Changelog

## 0.11.0 — Verified name remediation (beta)

- Add explicit, per-network opt-in automatic correction of generic Google Wi-Fi
  client names using unambiguous exact HA MAC matches. Personalized Google names,
  IP-only matches and conflicting identities remain unchanged.
- Verify the historical Android request schema: `PUT stationName` uses `name`;
  `DELETE stationName` restores automatic naming. Record the sources and limits in
  [automatic naming](docs/NAME_SYNC.md). No live Google-account trial is claimed.
- Recheck fresh Google identity and the HA proposal before each write. Persist
  intent first, require fresh read-back for completion and never replay an
  uncertain write. Rejected/unconfirmed results pause automatic work.
- Limit automatic batches to three candidates per config entry every five
  minutes, driven by normal successful polls. Disable remains available during
  outages. Reloads preserve settings and pause unfinished requests.
- Add administrator controls for individual application, automatic naming,
  read-only verification and guarded undo, with private local history. Undo
  excludes a client from subsequent automatic batches.
- Keep the map and HA label in agreement after verified naming, without repeating
  an identical HA name in parentheses. Keep detailed naming history out of
  shareable diagnostics and Recorder attributes.
- Extend isolated API, real HA service/lifecycle and frontend tests, plus the
  fictional management demo, for naming and recovery behavior.

Installing the release does not enable automatic naming. This release does not
install or restart a household HA. The unofficial API remains beta and backend
acceptance must be confirmed by runtime read-back.

## 0.10.0 — Point areas and management (beta)

- Add a Management page to the bundled panel, with English/Portuguese labels
  following the HA user language and keyboard navigation across all three views.
- Map points to existing HA areas using administrator-checked, entity-scoped
  services. Store mappings separately per config entry, network and point.
- Add a WiFi associated area sensor for clients. It follows the explicit current
  wireless point and clears when disconnected, wired, unmapped, unknown or offline.
  Failed network polls remain unavailable. Fixed HA device areas are never moved.
- Update mappings after HA area renames/deletions without polling Google. Preserve
  mappings across reloads, and display area estimates on the map.
- Group network/point restarts and Internet, mesh, local and client speed tests
  with target/network confirmation and existing provider operation feedback.
- Add read-only name proposals for generic Google client names, using exact MAC
  identity only. Preserve personalized names, ambiguous matches and IP-only
  matches. Copy proposals for manual use in Google Home; automatic cloud rename
  remains unavailable until its request schema and read-back are validated.
- Preserve mapping drafts, focus and scroll during regular HA state updates.
  Discard responses from a previously selected network and avoid automatic retries
  of failed management loads or uncertain writes.
- Extend isolated HA, frontend and fictional-demo validation for management.

This release does not install or restart a household HA. Google rename writes,
physical room tracking and BSSID pinning are not claimed capabilities.

## 0.9.3 — Stabilization

- Isolate per-network cloud failures. A denied, unreachable or malformed network
  no longer discards successful readings from other networks in the same account.
  Authentication and rate limits still apply to the whole account session.
- Preserve failed networks' known layout/IDs as unavailable and reject new writes
  using stale snapshots. Recovery reuses the existing entities and devices.
- Keep stable map routing metadata when HA removes unavailable live attributes.
- Use valid lowercase HA enum states for band/connection sensors, declare optional
  framework dependencies and pass authentication links as translation placeholders.
- Preserve JSON and page scroll while the map rebuilds its layout, including
  browsers that clamp scroll positions when reused information panels detach.
- Refresh provider network/point names and point firmware in our device registry
  records while preserving user names and existing IDs.
- Disable optional client raw-telemetry/capability sensors and selected point
  diagnostics by default on new entities. Existing enabled entities stay enabled.
  The map carriers, cached histories and `get_google_metrics` remain available.
- Require explicit options for experimental group/insight actions and a separate
  opt-in for point/network removal, retaining administrator and name checks.
- Remove AP identifiers from diagnostic cache keys and hexadecimal identity keys
  from radio field evidence. Raw information views remain private network data.
- Allow deliberate manual removal of obsolete integration device records only
  after a complete successful discovery no longer reports them.
- Reject link-local point addresses consistently with the other LAN transports.
- Add adversarial HTTP/RPC, permission, lifecycle and synthetic 100/300-client
  tests. Test HTTP is restricted to loopback; no live HA credentials are required.
- Add branch coverage measurement with a 90% CI floor, minimum/latest HA test
  jobs, HACS/hassfest validation, dependency audits and Dependabot configuration.
- Add local original brand assets, reproducible manual archives, package checks,
  English security/support/recovery guides and an explicit 1.0 readiness checklist.

The 0.9.3 release is still beta. It does not install itself on an existing HA
instance. Physical compatibility, independent onboarding and a prolonged community
trial remain required before 1.0. See [release readiness](docs/RELEASE_READINESS.md).

Upgrade note: automations comparing the `wireless_band` or `connection_type`
sensor state must now use lowercase values (`band_5000_mhz`, `wireless`, `wired`,
etc.). Entity IDs and the original provider values in client map attributes stay
unchanged. Display labels remain localized.

## 0.9.2

Reduce duplicated client telemetry and exclude large diagnostic payloads from
Recorder attributes, retaining numeric metric history and map carriers.

## 0.9.1

Make information sections clearly expandable/collapsible and retain JSON scroll
and keyboard focus during live updates.

## 0.9.0

Add cached supplemental Google/LAN reads, firmware notes and LAN/WAN information.

Earlier authentication, mesh-test and operation-feedback changes are described in
the [published releases](https://github.com/spkon/ha_google_wifi/releases).
