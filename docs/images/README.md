# Screenshot provenance

Except for the area-following image noted below, screenshots in this directory
were captured in a browser on 2026-10-16 from the **0.12.2** panel components,
imported directly by `tools/demo.html`.
They show the shared network selector, manual naming controls and revised layouts.
Automatic naming remains disabled. The Management and Locations captures use the
fictional multi-home scenario; the mobile capture validates a 390-pixel viewport.
The surrounding Home Assistant sidebar/header is a simulated demo frame, not a
connection to a Home Assistant instance. The component layout and behavior are
the released code; the demo does not override their templates or styles.

The default fixture has four points and 24 clients. The multi-home scenario adds
a fictional two-point workshop with one client and one local-status point. Every device name, area, address,
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
| `locations-demo.png` | Independent networks labeled by home/building. |
| `connection-guide-demo.png` | Connection steps reached from a local-status network. |
| `management-mobile-demo.png` | Management on a narrow screen, with every tab and the single network selector visible. |
| `area-following-demo.png` | The 0.13.0 client area-following controls, with only Google WiFi records enabled in the fictional demo. |

Each image is an ordinary viewport capture, so some continue below the visible
area as in Home Assistant. Browser JPEG captures are converted to PNG without
cropping, compositing, retouching or changing the content. Keep PNG filenames
stable when refreshing images so existing documentation links continue working.

To reproduce the views, follow [the browser-demo instructions](../TESTING.md#browser-demo).
Never replace these fixtures with live HA/Google responses to refresh a screenshot.
