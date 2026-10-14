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

Existing entities are preserved. This change does not disable entities, rename
IDs, remove devices, change polling intervals or alter the WiFi network.

Backend Python changes require a planned Home Assistant restart to take effect.
Reloading a config entry alone does not reliably load changed Python modules.
Keep a configuration backup and verify the map, identities, metrics and action
feedback after installation. Do not purge existing Recorder history as part of
this update.
