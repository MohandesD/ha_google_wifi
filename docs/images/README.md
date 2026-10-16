# Screenshot provenance

The screenshots in this directory were captured in a browser on 2026-10-16 from
the released **0.11.0** panel components, imported directly by `tools/demo.html`.
`naming-demo.png` was refreshed from **0.11.1** to show the one-time batch controls
and a selected fictional device while automatic naming remains disabled.
The surrounding Home Assistant sidebar/header is a simulated demo frame, not a
connection to a Home Assistant instance. The component layout and behavior are
the released code; the demo does not override their templates or styles.

The fixture has four points and 24 clients. Every device name, area, address,
measurement, firmware note, speed test and usage record is invented. IPs use
documentation ranges `192.0.2.0/24` and `198.51.100.0/24`; MACs/BSSIDs use a
locally administered `02:00:00` prefix. The demo user is not an actual account.
Measured RSSI is assigned only to the six fictional Shelly relays. Google
ratings and missing measurements remain separate.

These images are not exports or redacted copies of a household dashboard. No
household tokens, names, inventories, addresses, usage records or screenshots
are inputs to the fixture. The demo's content policy forbids API connections,
and network control calls are disabled. Name/area workflows only update local
JavaScript objects.

| Image | View |
| --- | --- |
| `overview-demo.png` | Overview metrics and all four point cards. |
| `devices-demo.png` | Device list, Google quality and measured RSSI. |
| `device-demo.png` | Open fictional relay details, identity, signal and usage. |
| `mesh-demo.png` | Google's point-to-primary assessments. |
| `map-demo.png` | Scrolled client-to-point map with fictional IPs/MACs. |
| `management-demo.png` | Point-to-area mapping. |
| `naming-demo.png` | An exact-MAC name proposal; automatic naming is disabled. |

Each image is an ordinary viewport capture, so some continue below the visible
area as in Home Assistant. Browser JPEG captures are converted to PNG without
cropping, compositing, retouching or changing the content. Keep PNG filenames
stable when refreshing images so existing documentation links continue working.

To reproduce the views, follow [the browser-demo instructions](../TESTING.md#browser-demo).
Never replace these fixtures with live HA/Google responses to refresh a screenshot.
