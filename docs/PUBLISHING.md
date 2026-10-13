# Publication checklist

The prepared repository is `spkon/ha_google_wifi`, version 0.7.0. Ownership links
and maintainer metadata are set. Code upload to the existing private repository
is authorized; changing visibility and adopting a licence await the owner's
decision. A proposed MIT text is available in [LICENSE-MIT.md](LICENSE-MIT.md).

Before making the project publicly installable:

1. Confirm the project licence and add its full text as `LICENSE`.
2. Make this reviewed repository public. HACS only supports public repositories.
3. Set a description such as “Google WiFi/Nest WiFi insights, usage history and
   controls for Home Assistant”, and topics `home-assistant`, `hacs`, `google-wifi`.
4. Review GitHub Actions results and publish a release matching manifest 0.7.0.
   Releases are optional for HACS: the default branch works without a release.
5. Optionally submit the integration to Home Assistant Brands and the default
   HACS catalogue. Those are separate processes, not completed by uploading code.

The HACS integration layout contains all runtime/UI files inside
`custom_components/google_wifi_insights`. The sidebar panel serves bundled assets
and configures itself after setup. Credentials, LAN captures and deployment tools
are excluded. Do not publish the surrounding Smart Home workspace.

Sources: [HACS general requirements](https://www.hacs.dev/docs/publish/start/) and
[integration layout/release requirements](https://www.hacs.dev/docs/publish/integration/).
