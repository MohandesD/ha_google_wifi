# Publication checklist

The repository is `spkon/ha_google_wifi`, version 0.7.1. Ownership links and
maintainer metadata are set. The owner approved public visibility and the MIT
licence. The full notice is included at the repository root and inside the
integration so that HACS installations also receive it.

For future releases:

1. Preserve the MIT notices and third-party attribution.
   Write all documentation, comments, docstrings and release notes in English.
2. Keep the repository public for HACS custom-repository installation.
3. Keep the description and topics relevant to Home Assistant and Google WiFi.
4. Review GitHub Actions results and publish a release matching the manifest.
   Releases are optional for HACS: the default branch works without a release.
5. Optionally submit the integration to Home Assistant Brands and the default
   HACS catalogue. Those are separate processes, not completed by uploading code.

The HACS integration layout contains all runtime/UI files inside
`custom_components/google_wifi_insights`. The sidebar panel serves bundled assets
and configures itself after setup. Credentials, LAN captures and deployment tools
are excluded. Do not publish the surrounding Smart Home workspace.

Optional donations are linked in the README and `.github/FUNDING.yml` through
[Buy Me a Coffee](https://buymeacoffee.com/spkon). Keep the funding link consistent
when updating these files. Donations do not unlock features or replace the MIT
license.

Sources: [HACS general requirements](https://www.hacs.dev/docs/publish/start/) and
[integration layout/release requirements](https://www.hacs.dev/docs/publish/integration/).
