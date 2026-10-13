# Firmware and LAN/WAN information

Available in 0.9.0. Open a point's information in the map for **Firmware and
updates**, **Firmware release notes**, **LAN information** and endpoint status.
The overview/map also include an expandable **Network configuration** section.
**All supplied information** shows the complete collected, sanitized metadata,
including hardware/account/group context and settings without dedicated sensors.

The public integration bundles these views automatically. Manually maintained
Lovelace installations must copy all five `www/*.js` modules and refresh their
resource versions; see [INSTALL.md](../INSTALL.md).

## Native Home Assistant diagnostics

Point devices have sensors for update status/channel/raw progress, offered
version, note count, information timestamp, LAN availability, WAN address/method/
gateway/prefix/lease, DNS mode and API environment. Binary sensors expose update
required, Internet online, Ethernet link and LAN-port link when returned.
Network devices expose configuration availability, WAN address/gateway/mode/
netmask, LAN address/netmask, DHCP pool boundaries and DNS mode, plus IPv6, UPnP
and guest-network flags. These are diagnostic entities; existing IDs are kept.

The firmware-note sensor includes `firmware_information`; LAN availability
includes `lan_information`; network-information availability includes
`network_information`. The same objects appear in filtered Google telemetry and
`get_google_metrics`. Large information attributes are excluded from Recorder;
the scalar entity readings remain suitable for HA history.

## Source, freshness and meaning

Cloud and local point readings retain their own timestamps. An unavailable read
does not create a false/off flag or relabel an older value as fresh. Supplemental
endpoints show success, denial, unsupported status and stale readings separately.
Cloud online status does not prove a point's LAN HTTP interface is reachable.

The release-notes API can return historical notes even when queried using the
installed firmware. Each note retains its version; the view says when none
matches. Absence of matching notes is not evidence of a pending update.
`updateNewVersion: 0.0.0.0` is displayed as no offered version, with the original
value retained in diagnostics. `updateProgress` remains a **raw value** because
its scale has not been established; it is not converted to a percentage.
These reads do not provide a supported manual firmware-upgrade action.

LAN reads accept private IPv4 addresses already configured in a local-mode entry.
For a cloud-only installation, open the integration's polling options and enter
the reachable primary point's **LAN gateway (optional)**. Discovered online points
in that primary's subnet can then be read. A unique online primary, LAN role and
returned local address must agree. Ambiguous identical gateway addresses on
different online networks are rejected; names alone never choose a network.

Status uses a 60-second cache. Other LAN reads use a one-hour cache, a four-second
request timeout and four concurrent requests, within a 12-second cloud enrichment
budget. Unsupported/denied endpoints back off for six hours. Cloud group details
are cached for 15 minutes, preferences for one hour, hardware information for one
day and release notes for six hours per firmware version. These reads never
restart points, run tests, change firmware channels or configure the network.

All returned non-credential fields from the supported reads are retained within
the existing transport/metadata limits. Passwords, tokens, usernames, setup/PIN/
pairing codes, security proofs and raw provider HTML are excluded. Release-note
HTML is converted to text and escaped again by the UI. Failed diagnostic-report,
connected-device and unverified provisioning endpoints are not polled.

The observed data still does not include radio airtime, retry/noise counters,
pairwise RSSI or every physical mesh hop. See [API_ENDPOINTS.md](API_ENDPOINTS.md)
for live endpoint observations and protocol references.
