# Changelog

## 0.9.3 — Stabilization

- Isolate per-network cloud failures. A denied, unreachable or malformed network
  no longer discards successful readings from other networks in the same account.
  Authentication and rate limits still apply to the whole account session.
- Preserve failed networks' known layout/IDs as unavailable and reject new writes
  using stale snapshots. Recovery reuses the existing entities and devices.
- Keep stable map routing metadata when HA removes unavailable live attributes.
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
