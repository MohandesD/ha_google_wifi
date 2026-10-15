# Credits and dependencies

Google WiFi Insights is an independent Home Assistant custom integration.

- [Home Assistant](https://github.com/home-assistant/core): host platform and API.
  Apache-2.0 license. Home Assistant is installed separately, not bundled.
- [gpsoauth](https://github.com/simon-weber/gpsoauth): Google Play Services
  authentication dependency, MIT license, copyright Simon Weber. Its source is
  installed separately by Home Assistant, not vendored here.
- [googlewifi-api](https://github.com/djtimca/googlewifi-api): community reference
  for Google WiFi endpoints and response fields. Its upstream package declares
  Apache-2.0. The downloaded investigation files are not included in this repository.
- [Shelly WiFi RPC documentation](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/WiFi/):
  reference for supported signal measurements and roaming settings.

Dependency licenses remain applicable to their respective projects. This
repository's own code is licensed under [MIT](LICENSE).
See [publication steps](docs/PUBLISHING.md).

The `brand/` SVG and PNG mark is original project artwork under MIT. It uses generic WiFi/network geometry and is not a Google, Nest or Home Assistant logo. Pillow is a development-only renderer; it is not bundled into the integration.
