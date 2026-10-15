# Installation

This is an experimental community integration, published under the MIT licence.
It is a Home Assistant custom integration, not a Supervisor add-on.

## HACS installation

Add `https://github.com/spkon/ha_google_wifi` in
**HACS → menu → Custom repositories**, type **Integration**. Download **Google
WiFi Insights**, restart HA and add the integration in **Settings → Devices &
services**. The bundled overview/map registers automatically after configuration.

## Manual installation

1. Download this repository or the manual-install archive.
2. Copy the entire `custom_components/google_wifi_insights` directory, including
   its `frontend` subdirectory, into `/config/custom_components`.
3. Restart HA and add **Google WiFi Insights** in **Devices & services**.
4. Choose local point status or Google account access; both entries can coexist.

Local mode reads status, firmware and uptime. Enter the names and addresses from
your own network, one per line. These are illustrative addresses only:

```text
Main point=192.168.50.1
Additional point=192.168.50.2
```

The form's editable initial address `192.168.86.1` is Google's common default
gateway, not a required address. Configure each point's actual address. The
current parser accepts 1–10 unique private IPv4 addresses.

## Google authentication

Choose **Get a token in the browser (recommended)** in the Google account setup.
The form includes a Google sign-in link and instructions for locating the
`oauth_token` cookie. Use a full desktop Chrome or Edge browser and paste the
cookie value directly in HA with the matching Google email. The Android ID is
handled automatically. The Google page can keep loading after **I agree**;
check whether the cookie exists before repeating sign-in.

The advanced method accepts an existing reusable master token together with its
original Android ID. A failed network check after exchange can be retried without
exchanging the cookie again while the flow stays open. Renew an existing entry
through **Configure → Renew Google authentication**; polling settings are under
**Configure → Polling and local points**.

See [the authentication guide](docs/AUTHENTICATION.md) for each step, missing
cookies, specific errors, retries, token types and credential renewal. Google
access remains unofficial; obtaining the browser cookie is still manual.

Treat Google tokens like passwords. Do not put them in issues, screenshots,
shared configuration files or source control. Home Assistant stores the reusable
token in the integration's configuration; backups should be protected too.
HA diagnostics from this integration omit account and device identity values.

## Automatic map and overview

Open **Google WiFi** in the sidebar after setup. The integration serves all UI
files itself; copying JS to `/config/www` or registering Lovelace resources is
unnecessary. A pre-existing panel at `/google-wifi-insights` is preserved, and
the integration uses `/google-wifi-insights-integration` instead. Removing the
last integration entry removes only its own panel, preserving user dashboards.
HTTP asset registration is shared by entries and reused on reload.

The map includes all available network scopes; the overview chooses the first
available network. Existing manual cards can still set `network_entity` using
an entity from that user's network. The overview accepts a local `map_path` to
link to a chosen map view. The map has a **Back to overview** link at the top.
It stays inside the bundled panel and automatically returns from a manual
`mapa`, `map` or `diagnostics` route to the same dashboard's `overview` route.
For different view names, set `overview_path: /your-dashboard/your-overview`
on the map card. Both navigation paths must be local Home Assistant paths.
User language follows HA, with English/Portuguese UI.

### Optional cards in another dashboard

Copy all five `www/*.js` files to `/config/www` and register
`/local/google-wifi-insights-map.js?v=0.9.3` and
`/local/google-wifi-dashboard-ui.js?v=0.9.3` as JavaScript modules.
Create a manual dashboard with `dashboard-overview.yaml` or `dashboard-map.yaml`.
Shared model/history modules are imported automatically. This is optional and
does not replace the bundled sidebar panel. Native tables use `dashboard.yaml`.

### Updating and troubleshooting

- HACS updates the integration and bundled assets together. Restart HA and
  reload the browser after an update. A manual install must also copy `frontend/`.
- Keep the existing `google_wifi_insights` domain and entries; reinstallation is
  not needed when upgrading from 0.6.1. Existing manual dashboards remain usable.
- No clients in local mode is expected: configure Google access to obtain them.
- If the sidebar is missing, confirm the entry loaded and HA frontend is enabled.
  Check HA logs for the integration; reserved panel-path collisions are preserved.
- Grey/unknown signal means no valid measurement. Historic gaps are not zero.
- Authentication failures require reauthentication in the HA form. Never send
  passwords/tokens in issues. Use the integration's redacted HA diagnostics and
  [authentication troubleshooting](docs/AUTHENTICATION.md).

## Measurements and controls

Open a client's Google WiFi Insights device in **Devices & services** to find its
reported IP, MAC, traffic, signal and other available entities. Eligible Shelly
clients also have roaming controls. An interval of zero disables roaming scans.
Enabling roaming restores the most recent positive interval remembered in this
integration session, or 60 seconds when none is remembered.

Polling defaults to 120 seconds and is configurable from 60 to 3600 seconds in
the integration options. Normal polling reads saved results and usage history;
it does not start tests or reset points. Native controls allow deliberate tests,
restarts, client pauses/priorities and point-light changes. Advanced services
provide typed group management and other actions with administrator confirmation.
See [the capability inventory](docs/CAPABILITIES.md) for details.

Usage graphs show rolling 1-hour, 24-hour, 7-day and 30-day windows. Missing
buckets stay unknown; charts show partial coverage, and complete-total sensors
remain unknown until all expected records exist. Saved WiFi tests show their
original date and tested point separately from current point and traffic.

## Updating to 0.9.3

Keep the existing config entries, integration domain, dashboards and registry
records. Make a protected backup and choose a maintenance window: replacing the
Python files needs a Home Assistant restart. This release does not remotely
install or restart anything.

HACS users select the published 0.9.3 release. Manual users replace the complete
integration directory, including `frontend/`, `brand/` and the license. Restart
HA once, reload the browser and verify the entry, map, device IDs and action
feedback. The new source/package/frontend versions are synchronized by release
checks; copying only the Python files is incomplete.

New optional client diagnostics (raw telemetry timestamp, WiFi capability and
spatial streams) and selected point diagnostics default to disabled. Existing
enabled entities stay enabled. Enable individual diagnostics on the device's
entity page when needed. Network/point map carriers remain active, and full
collected metrics remain available through `get_google_metrics`.

Under **Configure → Experimental and destructive controls**, both switches
default to off. Advanced group/insight services need experimental opt-in.
Point/network removal needs that opt-in plus removal opt-in, an interactive
administrator and the existing exact-name confirmations. Existing advanced
workflows must deliberately enable these options; ordinary controls are unchanged.

If one cloud network fails, other networks continue updating. A previously known
failed network keeps its layout/IDs as unavailable; cached traffic and RSSI are
not shown as fresh readings and new writes are rejected. If authentication or
throttling affects the account, HA reports that account failure normally.

## Rolling back

Download the previous release through HACS **Redownload → version**, or restore
the previous complete integration directory in a manual install. Keep config
entries and device/entity registry records. Restart HA during a maintenance
window and reload the browser. The 0.9.3 update introduces no config-entry schema
migration, so its data remains compatible with 0.9.2. Earlier releases do not
enforce the new experimental/removal switches; restoring 0.9.2 restores its old
control policy. A rollback has not been performed on the household HA as part of
this release.

Restore a full HA backup only when necessary, with its emergency recovery key
stored separately. Do not edit `.storage`, purge Recorder history or delete
device records as an update/rollback shortcut.

## Removing the integration or obsolete devices

1. Delete each Google WiFi Insights entry in **Settings → Devices & services**.
   HA removes its integration entities/devices and its bundled panel after the
   last entry. Other integrations' device records and user dashboards are retained.
2. Remove the downloaded integration through HACS, or remove only its own
   `custom_components/google_wifi_insights` directory in a manual installation.
3. Remove optional manually registered Lovelace resources/cards only if you added
   them yourself. A restart may be needed to unload Python modules from memory.
4. Follow [the credential-retirement guidance](SECURITY.md#removing-or-replacing-access).
   Removing an HA entry does not revoke Google-side access or old backup copies.

An obsolete integration device can be deleted manually after a complete,
successful discovery no longer reports it. The integration refuses removal of a
currently known device or while discovery is incomplete. Sleeping or disconnected
clients are not automatically deleted; Google can retain them in its client list.
