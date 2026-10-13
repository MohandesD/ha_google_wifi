# Google WiFi Insights 0.7.1

This custom integration collects the network, points and clients returned by the Google account, without household-specific names, addresses or IDs in the runtime.

Version 0.7.0 bundles the existing metrics/actions UI for HACS installation and registers the sidebar panel automatically. Metrics/actions retain the 0.6.1 behaviour.
Version 0.7.1 standardizes documentation and examples in English and adds optional
funding links. Metrics, controls and interface translations retain their behaviour.

## Collected data

| Source | Collected information |
| --- | --- |
| Groups / status / stations | Network settings and capabilities, firmware, point status, client names, IP addresses, WiFi band/capability, explicit point association, last seen, pause policies and priority expiry |
| Realtime metrics | Current WAN and client download/upload, Google client/mesh ratings and all additional returned metadata |
| Saved Internet tests | Download/upload Mbps and test timestamp |
| Saved client WiFi tests | Throughput Mbps, timestamp and **tested point**; old tests remain old tests |
| Saved mesh tests | Point throughput Mbps and timestamp |
| Backhaul | Google's returned backhaul type/band; no inferred intermediate links |
| Historical usage | WAN and per-client bytes received/sent: minutes in a rolling hour, hours in 24 hours, days in 7 and 30 days; peak traffic records |
| Insights | Google advisory cards and their available actions/links |
| Local point status | Firmware, uptime and exposed local status metadata |
| Shelly local radio | MAC-verified RSSI, BSSID, channel and supported roaming settings |

Intervals are requested UTC rolling windows, not Google Home's local-calendar “today”. Bucket timestamps mark their **end**. Missing buckets remain missing: complete totals become unknown and charts identify the partial sample. Rolling totals are measurement sensors, never monotonic lifetime counters. Minute buckets may be interpolated or delayed by Google; requesting one-minute granularity does not prove one-minute physical sampling.

All additional returned non-credential fields are retained in telemetry or the `get_google_metrics` response. Histories remain cached in memory; full histories are requested through `get_usage_history`, avoiding a copy of every minute bucket on every entity. Normal polling reads results; it never starts benchmarks or restarts the network.

## Controls

Native HA entities provide point/network restart, Internet/mesh/local/client tests, pause/resume Internet access for clients, one-hour priority, clearing priority, point-light brightness and forced metric refresh. “Test clients” runs Google's point-level WiFi client test, not a promised single-client benchmark.

The `google_wifi_insights.google_action` service additionally accepts timed pauses/priorities, group pause/resume, create/update/delete device groups, insight dismissal/server actions and removal of a point/network. Targets must be real integration registry entities from the current network. Advanced operations need an interactive HA administrator and exact network-name confirmation. Removal additionally requires the exact target name and may erase the network configuration; no removal buttons are created. Link-only insight cards do not become invented server actions.

```yaml
action: google_wifi_insights.google_action
data:
  entity_id: sensor.example_client_connected_point
  action: prioritize_client
  parameters:
    duration_minutes: 120
```

```yaml
action: google_wifi_insights.get_usage_history
data:
  entity_id: sensor.example_client_connected_point
  resolution: minute  # minute, hour, day, month
response_variable: wifi_history
```

`get_capabilities` returns read availability, collected timestamps and action support status. `get_google_metrics` returns the collected telemetry and, for network targets, all cached saved-test results. These services require administrator access for user-initiated requests. Trusted HA automations can use ordinary controls; advanced/removal operations require an interactive administrator.

An HTTP acknowledgement is not proof that an action completed. Operation IDs are polled, failures and unconfirmed delivery are shown, and settings are read back. A timed-out write is **not retried automatically**. Actions are labelled `not_tested` until used; collecting a network does not establish permission to write it.

## Limits made visible in HA

This is an unofficial Google API. The capability inventory distinguishes implemented operations, successful reads, provider denials and unverified functions. It does not claim universal access to every Google Home feature.

The public endpoint inventories also mention guest WiFi, SSID/password, DNS, DHCP/static addresses, UPnP/IPv6/port forwarding, schedules/content filtering and client renaming. Their complete write schemas have not been verified, so this release collects their returned settings but does not send guessed configuration writes. Passwords, OAuth tokens, sensitive account data and opaque mesh configuration are excluded from telemetry. Client BSSID pinning, radio airtime/noise/retries and physical mesh routes are not supplied by the observed endpoints.

## Protocol references

- [Original GoogleWiFiDesktop developer: historical usage date range and granularity](https://www.reddit.com/r/GoogleWiFiDesktop/comments/h9aw1a/)
- [djtimca/googlewifi-api: Foyer API operations](https://github.com/djtimca/googlewifi-api)
- [JamesHawkinss/google-wifi-api-node: typed operations and results endpoints](https://github.com/JamesHawkinss/google-wifi-api-node/blob/master/index.js)
- [Original Android endpoint inventory](https://github.com/olssonm/google-wifi-api/issues/6)
- [Home Assistant frontend context API](https://github.com/home-assistant/frontend/blob/dev/src/data/context/index.ts)

Live validation must distinguish safe reads/settings from disruptive tests/reboots and destructive operations. The latter are available for deliberate use, not automatically executed during installation.
