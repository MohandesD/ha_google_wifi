# Google WiFi Insights

Google/Nest WiFi custom integration for Home Assistant: network overview, client
association map, usage history, available Google controls and local Shelly RSSI.
It can coexist with Home Assistant's official `google_wifi` integration.

**Beta 0.7.0.** This repository is `spkon/ha_google_wifi`. The project is public and licensed under MIT. It is an
unofficial community integration, not maintained by Google or Home Assistant.

## Install with HACS

1. Open **HACS → menu → Custom repositories**.
2. Add `https://github.com/spkon/ha_google_wifi` as **Integration**.
3. Find **Google WiFi Insights**, download it and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Google WiFi Insights**.
5. Choose **Google account and clients** for full network/client data, or local
   point status for firmware/uptime. Both entries can coexist.
6. After configuration, open **Google WiFi** in the sidebar. The overview and map
   are included: no separate JavaScript copy, Lovelace resource or YAML is required.

HACS custom-repository installation is separate from inclusion in its default
catalogue. The project has not been submitted to Home Assistant Brands or the
default HACS catalogue. See [INSTALL.md](INSTALL.md) for Google authentication,
manual installation, upgrades and troubleshooting, or [Portuguese instructions](docs/INSTALL-PT.md).

## What you get

- Account-discovered networks, points and clients; explicit client-to-point
  association, presence, IP/MAC, band/capabilities and last-seen data when supplied.
- `Google name (Home Assistant name)` matching through exact MAC or an unambiguous
  current IP. Other integrations' device records are preserved.
- Google's connection/mesh ratings and current download/upload traffic.
- Saved WAN, client WiFi and mesh speed tests with original dates/tested points.
- Network and client usage graphs: minutes over one hour, hours over 24 hours,
  days over 7 or 30 days, with partial coverage visible and no invented zeroes.
- Point/network restarts, tests, client Internet pause/priority, point lights and
  typed administrator services for supported group/insight actions.
- MAC-verified Shelly RSSI/BSSID/channel and eligible roaming controls.
- English/Portuguese UI following Home Assistant's user language and time zone.
- Sanitized additional telemetry, capability status and explicit operation results.

The [capability inventory](docs/CAPABILITIES.md) distinguishes implemented actions,
verified reads and configuration features whose write schemas remain unverified.
Normal polling does not run benchmarks or restart points. Destructive operations
have no buttons and require deliberate administrator confirmation.

## Requirements and limits

Validated with **Home Assistant 2026.10.1**, **Python 3.14** and **Node.js 24** for
development tests. HACS conservatively requires HA 2026.10.1, the version tested;
older versions and all Google/Nest models have not been validated.

Google account access uses undocumented endpoints and `gpsoauth==2.0.0`.
Authentication can change or fail. Google ratings are categories, not measured
dBm. Local mode accepts 1–10 reachable private IPv4 points. Shelly access supports
registered, MAC-matched Gen2/Gen3/Gen4 devices with authentication disabled and
compatible WiFi RPC; only roam threshold/interval are changed.

Usage windows are rolling UTC intervals, not Google Home's calendar-day totals.
Missing intervals remain unknown. Stored speed tests are not live traffic.
The observed Google endpoints do not expose BSSID pinning, radio airtime/noise/
retries or every physical mesh hop. Counts and traffic do not prove saturation.
Guest WiFi/DNS/DHCP/port-forwarding and other unverified configuration writes are
catalogued but not guessed.

Tokens stay in Home Assistant's integration configuration. Never put tokens,
personal inventories or unredacted diagnostics in this repository or its issues.

## Development and validation

```sh
python -m venv .venv
# Activate it, then:
python -m pip install -r requirements-dev.txt
python -m pytest -q
npm test
python tools/sync_frontend.py --check
python tools/build_package.py
```

The tests use synthetic fixtures and an isolated real HA framework; they need no
Google account, LAN devices or private captures. The frontend development files
in `www/` have byte-identical bundled copies inside `custom_components`; run
`python tools/sync_frontend.py` after editing them. CI checks the copies and tests.

See [validation/audit](docs/AUDIT.md), [credits](CREDITS.md) and
[publication checklist](docs/PUBLISHING.md). The running private installation
remains at 0.6.1 until deliberately upgraded; 0.7.0 adds bundled UI registration.
