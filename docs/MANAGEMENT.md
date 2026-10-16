# Point areas and network management

Version 0.11.0 provides **Management** alongside **Overview** and **Map** in the
integration's sidebar panel. It requires a Home Assistant administrator and a
currently available Google account network. Local-only mode has no cloud client
association inventory. Existing dashboard cards keep working; the Management
page is part of the bundled sidebar panel.

From version 0.12.2, use the shared **Network** selector above the page. Management
requires one Google account network, so it replaces **All networks** with an
explicit cloud target. The selected home still limits the available networks;
an outage does not silently switch actions to another home. Standalone management
cards retain their own selector. The refresh control reads cached data only.

Version 0.12.0 adds a shared location/network filter and a **Locations** page for
multiple homes and setup guidance. [Location labels](LOCATIONS.md) are independent
of the existing point-to-area mappings below. Assign each cloud network its home
before mapping points when accounts expose more than one house.

![Point and area management with fictional data](images/management-demo.png)

## Map points to existing areas

1. Create the required areas in Home Assistant if they do not already exist.
2. Open **Google WiFi → Management** and select the intended network.
3. Choose an area for each point and press **Save area**.
4. Choose **No area mapped** and save to remove a mapping.

Mappings are local to this integration, keyed by config entry, Google network ID
and point ID. Point names are labels, not identity keys. Renaming a point does
not lose the mapping. Several points may share one area. This does not rename
Google rooms or change the area of any HA device, including the point itself.
Mappings survive HA/integration reloads and are included in HA configuration
backups. Removing the integration entry deletes its local mappings. Area renames update the displayed names; deleting an area clears its
effective association. Create a new mapping if that area is later replaced.

Each client gets a **WiFi associated area** sensor. For example, a phone connected
to a point mapped to **Example office** reports that area. When Google's next
successful poll associates the phone with a point mapped to **Example studio**,
the sensor reports **Example studio**. No fixed HA device area is moved.

The sensor exposes `associated_area_id` and `area_source: wifi_point`. The same
fields appear on the canonical Connected point sensor used by the map. The sensor
is `unknown` for disconnected or wired clients, missing/unknown points, unmapped
points and points not currently reported online. It is `unavailable` when the
coordinator or that network is unavailable. Old area values must not be treated
as current presence during an outage.

This is **association-based coverage estimation**, not room positioning. A phone
can stay attached to a more distant point. Cloud reporting and the configured
poll interval add delay, and private/randomized MAC addresses can change device
identity. Do not use it as the sole input for safety-critical occupancy actions.

Use the area ID attribute for automations if you want area renames to be harmless:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.example_phone_wifi_associated_area
    attribute: associated_area_id
    to: example_office
    for: "00:02:00"
conditions:
  - condition: template
    value_template: >-
      {{ states('sensor.example_phone_wifi_associated_area')
         not in ['unknown', 'unavailable'] }}
actions:
  - action: persistent_notification.create
    data:
      title: Wi-Fi area association
      message: Example phone has been associated with the office point for two minutes.
```

Replace the fictional entity and area IDs with the values shown by your HA. The
example creates a local HA notification; it does not switch lights or change the
network.

## Name review

![Name review with a fictional exact-MAC match](images/naming-demo.png)

The page offers HA name suggestions for blank, station-ID, MAC-like and known
generic Google labels such as **Unnamed Device**. A suggestion requires a valid
exact MAC match, one agreed HA name and one Google station for that MAC within
the selected network. IP-only matches and conflicting device names are skipped.
Personalized Google names and non-placeholder hostnames are preserved. Opening
the page does not modify any name.

Use **Apply name in Google** to review and confirm an individual suggestion.
To rename several devices once, tick their checkboxes and use **Rename selected**,
or choose **Rename all eligible**. Review the complete network/name/MAC list and
confirm. These actions leave automatic naming unchanged. From version 0.12.1,
up to three devices run concurrently with individual identity checks, durable
intent and read-back verification. Each group finishes before the next begins.
The panel shows active, verified, skipped, review and not-sent counts. A rejected
or unconfirmed result stops new requests; already active requests may still
complete. Keep the page open; **Stop pending requests** stops the remaining queue
without recalling sent requests. Pending journal entries cannot be selected for
another batch. An older backend retains serial behavior and shows an upgrade
notice until the complete integration is updated.

To continue correcting new generic names automatically, expand **Automatic naming**
below the suggestions, use **Enable automatic naming** and confirm the selected
network. This optional section starts collapsed; its current status remains visible.
The setting starts disabled and is
saved separately for each account entry and network. **Disable automatic naming**
stops subsequent requests, including during outages. An in-flight request cannot
be recalled.

**Recent name changes** records the original name, requested name and verification
state. **Verify result** reads Google without repeating an uncertain write.
**Undo name change** requires a verified, latest rename and the same current
Google name/MAC. Undo excludes that client from future automatic batches.

The request schema is established from the Google Android client, while live
acceptance depends on the account and backend. No new household Google-account
trial was performed for this release. Read [automatic naming](NAME_SYNC.md) for
request provenance, fresh identity checks, bounded batches, recovery and privacy.
The copy/manual Google Home workflow remains available when desired.

## Quick actions and feedback

The page groups existing network/point actions: Internet speed test, restart
network, restart point, local speed test, client WiFi test and mesh test toward
the explicitly identified primary point. The primary point has no mesh-to-self
test. Every request presents the exact target and selected network before a
separate **Confirm request** click. Tests can affect throughput and restarts
temporarily interrupt connectivity.

Existing Google action feedback distinguishes accepted, running, completed,
failed and unconfirmed operations. Google accepting a request is not proof that
a point has restarted or a test completed. The UI never retries an uncertain
write. Refreshing this page reads cached HA data only; it neither runs tests nor
forces a Google poll.

## Services and privacy

| Service | Target and behavior |
| --- | --- |
| `google_wifi_insights.get_management` | Any verified current entity in the selected cloud network. Returns available HA areas, point mappings and name proposals. Requires a response. No extra Google request. |
| `google_wifi_insights.set_point_area` | A verified point entity and required `area_id`, using an existing area ID or `null` to clear. Saves locally and updates sensors immediately. Optional response returns the updated management view. |

The naming services are documented in [NAME_SYNC.md](NAME_SYNC.md).

Services use the same registry/config-entry/network verification as existing
controls and reject non-administrator user contexts and stale write targets. Cached management
remains readable during an outage, and automatic naming can still be disabled.
HA automations without a user context may call the mapping service, as with other
ordinary integration services. No arbitrary HTTP paths or arbitrary HA service
names are accepted by this page. Each network selector is scoped to its config
entry as well as network ID.

Names, area names, MAC addresses and HA device IDs are private network data. They
remain inside authenticated HA responses and local mapping storage; raw management
data is not added to the shareable integration diagnostics. The public demo uses
fictional devices and locally simulated area mappings, with real network actions
disabled.
