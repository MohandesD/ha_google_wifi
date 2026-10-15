# Publication checklist

The repository is `spkon/ha_google_wifi`, version 0.9.3. Ownership links and
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

## 0.9.3 release gates

Run all commands in [TESTING.md](TESTING.md), review minimum/latest HA jobs and
HACS/hassfest results, and inspect dependency audits before publishing. Use a
release/tag matching the manifest and attach the allowlisted manual archive with
its SHA-256. The archive has deterministic timestamps/permissions and LF text.
Do not publish private local audit evidence or the surrounding Smart Home folder.

Local `brand/` assets are provided for HA 2026.3+ and current HACS. A central
Brands submission is not needed for those assets. Default HACS catalogue inclusion
remains separate. Check the [readiness matrix](RELEASE_READINESS.md) before using
the word stable or announcing a 1.0 release. New independent/hardware observations
must be recorded as such; green mocked tests do not establish them.
