# State and history efficiency

The integration retains every metric, device ID, action and cached usage-history
response. The Connected point sensor carries the complete client information
needed by the map. Identity and control entities carry identity metadata rather
than duplicating changing traffic and radio samples across every client entity.
The RSSI sensor retains the origin and observation time of its own measurement.

Large diagnostic payloads remain visible in current entity attributes and through
the `google_wifi_insights.get_google_metrics` service. They are excluded from
Recorder attribute storage. Numeric metric states still retain their ordinary
history and statistics. Cached Google traffic history remains available through
`google_wifi_insights.get_usage_history` and the dashboard.

Existing entities and enabled/disabled preferences are preserved. The 0.9.2
attribute optimization does not rename IDs or alter the WiFi network.

Backend Python changes require a planned Home Assistant restart to take effect.
Reloading a config entry alone does not reliably load changed Python modules.
Keep a configuration backup and verify the map, identities, metrics and action
feedback after installation. Do not purge existing Recorder history as part of
this update.

## Optional diagnostics in 0.9.3

For new registry entities, these default to disabled:

- Clients: `google_telemetry_at`, `wireless_standard`, `rx_spatial_streams`.
- Points: `api_environment`, `wan_prefix_length`, `wan_lease_seconds`,
  `update_progress_raw`.

Existing enabled entities are not disabled during upgrade. Users can enable an
optional diagnostic from HA's entity page. Network/point raw-information carriers
and the Connected point/tracker/connectivity carriers stay available for the map
and usage history. `get_google_metrics` reads the collected data independently of
whether an optional sensor is enabled.

The integration still creates many entities for large inventories. Synthetic
scale evidence is attached to CI, with its limitations described in
[TESTING.md](TESTING.md). Measure actual Recorder growth and full HA memory in a
lab before making a long-running capacity claim.
