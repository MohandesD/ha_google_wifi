# Security policy

## Supported versions

Security fixes target the latest published 0.9.x stabilization release. The project
is still in beta; a 1.0 release requires the checks in
[release readiness](docs/RELEASE_READINESS.md). The Google authentication and WiFi
endpoints are unofficial and can change independently of this integration.

## Reporting a vulnerability

Use GitHub's **Security → Report a vulnerability** when that option is available.
If it is unavailable, open a minimal issue asking the maintainer for a private
reporting channel. Do not disclose the vulnerability or affected network details
in that initial public issue. There is no promised response time.

Never include Google/HA tokens, cookies, passwords, backup keys, account emails,
unredacted logs, raw telemetry or real network inventories. Reproduce issues with
fictional identifiers. Review diagnostic files before sharing them, including
files produced by older integration versions.

## Credential and data boundaries

- Google sign-in and account checks happen on Google's site. This integration
  never asks for the Google password and never reads browser profiles/cookies.
- The manually supplied browser token is exchanged for a reusable Google token.
  The reusable credential is stored in HA's config entry. Protect the HA host,
  config directory and backups. A masked form field is not encrypted storage.
- Google requests use HTTPS with certificate verification and do not follow
  redirects. Authentication runs in HA's executor with bounded timeouts.
- Local Google/Shelly reads use HTTP on explicitly selected private IPv4 devices.
  No Google credential is sent to those devices. Shelly reads/writes require a
  current registry MAC match and a fresh physical identity check before writes.
- HA diagnostics export counts and sanitized capability/field evidence. Raw
  `get_google_metrics` responses and dashboard information can contain device
  names, addresses and network configuration: they are not public bug reports.
- Network controls require administrator access for user-initiated calls. HA
  automations can use ordinary controls. Experimental actions additionally need
  opt-in, an interactive administrator and the exact network name. Removal needs
  a second opt-in and the exact target name. See [capabilities](docs/CAPABILITIES.md).
- An unavailable account/network cannot be used for new Google or roaming writes.
  Ambiguous writes are not automatically retried.

## Removing or replacing access

Deleting the integration entry removes its active HA configuration. It does not
revoke the Google credential at the provider or erase copies in old backups.
Review the associated Android/device sessions in
[Google Account security](https://myaccount.google.com/device-activity) when
retiring access. If a token may have been exposed, follow Google's account
security process and verify that the old credential is no longer accepted.
Changing an HA access token does not revoke a Google token. There is no claimed
automatic Google token-revocation endpoint in this integration.

## Automated checks

CI audits the manifest's runtime Python dependencies (including their resolved
dependencies) and npm development dependencies, runs Ruff, verifies public package
contents and exercises secret-safe failures. These checks do not constitute a
third-party security audit. Tests block external HTTP; their servers and HA
instances run locally with synthetic data.
