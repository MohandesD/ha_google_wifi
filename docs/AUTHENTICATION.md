# Google authentication

For multiple houses or a local-status entry without clients, start with
[Locations and connection setup](LOCATIONS.md). The dashboard guide distinguishes
missing client data from authentication failures and helps select the correct
Google account/home before renewing credentials.

Google WiFi Insights uses the unofficial Google Play Services authentication
method documented by [gpsoauth](https://github.com/simon-weber/gpsoauth#alternative-flow).
It does not offer a registered Google OAuth application or automatically read
Google cookies from your browser. Google sign-in, account checks and acceptance
of Google's terms take place directly on Google's site.

Version 0.8.0 adds a guided setup, specific error messages, a retry step and an
option to renew authentication. Existing account entries keep their stored
credentials, entry IDs, devices and polling options when upgraded. A working
entry does not need to be configured again.

## Recommended method: a browser cookie

1. In Home Assistant, open **Settings → Devices & services → Add integration →
   Google WiFi Insights → Google account and clients**.
2. Choose **Get a token in the browser (recommended)**. Keep the HA form open.
3. Open [Google sign-in](https://accounts.google.com/EmbeddedSetup) in a full
   desktop Chrome or Edge browser. A browser embedded in an app may prevent the
   sign-in flow from completing. A full browser is a troubleshooting option, not
   a guarantee that Google will accept the account.
4. Sign in using the same Google account that can manage the WiFi network in
   Google Home. Complete any two-step verification or account checks Google asks
   for. Read the terms and select **I agree** if you accept them.
5. The page may keep loading after acceptance. The upstream instructions describe
   this behaviour: check whether the cookie exists before starting over.
6. Press **F12** to open developer tools. Under **Application → Storage →
   Cookies**, select `https://accounts.google.com`. Find the cookie named
   `oauth_token` and copy its **Value**. Developer-tools labels may differ by
   browser language. Copy the complete value rather than the cookie name, table,
   request headers or a screenshot.
7. Return to the HA form. Enter that Google account's email, paste the cookie
   value in the masked field and submit. The integration handles the Android ID
   automatically and exchanges the cookie for a reusable token.

The browser cookie value starts with `oauth2_4/`. The form accepts surrounding
quotes, leading/trailing whitespace, a single `oauth_token=` assignment and a
URL-encoded value. It rejects a prefix without a value and whitespace inside the
token. An unsupported paste is rejected locally before contacting Google.

Initial validation checks authentication and network discovery. It does not run
speed tests, restart points or fetch every historical metric. Once the entry is
created, normal integration setup loads points, clients and available metrics.
A successful discovery check does not establish access to every optional Google
endpoint.

## If Agree appears stuck or the cookie is missing

First inspect the cookies in the same tab and browser profile where you signed
in. If `oauth_token` exists, continue with its value even if the page is still
loading. A spinning page alone does not prove failure or success.

If the cookie is absent, setup has not obtained a credential. Try the full
desktop browser, confirm that sign-in and Google's account checks completed,
and check whether browser extensions or cookie settings prevented the flow.
These are troubleshooting checks, not automatic workarounds for Google's
restrictions. Keep two-step verification enabled.

Do not paste JavaScript from an issue into Google's page, send your cookies to
third-party token generators, or share the token in chat. Only paste the token
directly into your own HA integration form.

## Advanced method: an existing reusable token

Choose **Use an existing master token (advanced)** only if you already have both:

- A reusable Google token beginning with `aas_et/` or `oauth2rt_1/`.
- The original Android ID used with that token: 16 hexadecimal characters.

Enter both in the advanced form, together with the matching Google email. An
arbitrary new Android ID is not a substitute for the original one. Use the
recommended browser method when the original pair is unavailable. If a token is
pasted into the wrong method, the integration opens the corresponding form and
asks you to paste it again; the token is never used as a default field value.

## Retry without exchanging the browser cookie again

If the cookie exchange succeeds but network discovery fails, the **Retry the
Google connection** step keeps the reusable token only in memory for that open
flow. Submit again to retry discovery; it does not exchange the original cookie
again. After a rate-limit error, wait before retrying.

Select **Choose another account or enter a new token instead** to discard the
pending credentials and return to method selection. Closing the flow or
restarting HA also discards pending credentials. A new browser cookie may then
be necessary. A Google rejection clears pending credentials and requests a new
token instead of treating the failure as a temporary network problem.

## Renew an existing entry

After updating the integration and restarting HA, open its entry under
**Settings → Devices & services → Google WiFi Insights**. Choose **Configure →
Renew Google authentication**. The options dialog opens HA's native
reauthentication flow. An already-open reauthentication flow is reused.

Choose the browser or advanced method and submit a fresh credential. Use the
same account as the existing entry. Validation completes before the entry is
updated; failed validation keeps the previous stored credential. Success reloads
that entry while preserving its identity, device/entity IDs and polling options.
Expired credentials also trigger HA's normal reauthentication flow automatically.

Polling settings remain under **Configure → Polling and local points**. Local
point-status entries do not have a Google authentication option.

## Understand the message

| Message | Meaning and next step |
| --- | --- |
| Wrong service token | The value resembles a Home Assistant or another service's token. Copy Google's `oauth_token` value. |
| Incomplete or invalid token | Copy the full cookie value, without the cookie table, embedded whitespace or extra cookies. |
| Google rejected the token | Obtain a fresh browser cookie with the same account, or verify the reusable token's original Android ID. |
| Google requires an account check | Complete Google's sign-in/security checks in the browser, then obtain a fresh cookie. |
| Authentication service unavailable | Check HA's Internet connection and retry later; this does not establish that the token is invalid. |
| Google requested a pause | Wait a few minutes before retrying. |
| No WiFi networks returned | Authentication succeeded but the account returned no networks. Confirm account access in Google Home. |
| Google denied network access | Check that account's Google Home permissions; a different HA token does not change them. |
| Network discovery failed | Retry the connection; the retry screen retains the exchanged reusable token while open. |
| Account mismatch | Renewal must use the same Google email as the existing entry. |

## Credential handling

The Google token, HA access token and Google password are different credentials.
This integration does not ask for your Google password. Its token field is masked;
raw credentials and provider response details are not included in error messages,
form defaults or diagnostics. Validated reusable credentials are stored in HA's
integration configuration, so protect HA backups as well as the live installation.
Keep tokens out of source control, issues and screenshots.

Implementation references: [gpsoauth alternative flow](https://github.com/simon-weber/gpsoauth#alternative-flow)
and [HA reauthentication](https://developers.home-assistant.io/docs/core/integration/config_flow/#reauthentication).

## First-time onboarding and retiring access

For community testing, follow this guide from a clean HA setup without maintainer
assistance. Record the browser, account type, HA version and the error category,
without account identifiers or token values. Complete Google's two-step checks;
do not weaken account security to make setup work. A managed account or embedded
browser may be rejected by Google, and this integration does not bypass that policy.

After success, verify the sidebar, network discovery and cached history before
trying any optional network control. A revoked/expired credential should open
HA's native renewal flow and keep existing device/entity IDs. Record independent
results in [release readiness](RELEASE_READINESS.md).

The reusable token is sensitive and is not a registered OAuth application secret.
Deleting the HA entry does not revoke access on Google's side or remove old backup
copies. See [credential retirement](../SECURITY.md#removing-or-replacing-access).
