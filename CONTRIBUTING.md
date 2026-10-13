# Contributing

Contributions to Google WiFi Insights are welcome. Use English for documentation,
code comments, docstrings, issue templates, pull request descriptions and release
notes. Keep dashboard examples and developer instructions in English too.

User interface translations are a separate concern: the interface follows the
Home Assistant user's language. Preserve supported translations and test fixtures
that verify them. New user-facing strings should have an English source text and
the appropriate translated entries.

## Development

Create and activate a Python virtual environment, then run:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
npm test
python tools/sync_frontend.py --check
python tools/build_package.py
```

Edit the four shared frontend modules in `www/` and run
`python tools/sync_frontend.py` to update their bundled copies. The sidebar panel
wrapper is maintained in `custom_components/google_wifi_insights/frontend/`.

The tests use synthetic fixtures and an isolated Home Assistant framework. Do not
commit credentials, private network inventories, unredacted diagnostics or local
deployment evidence. Include relevant validation in pull requests and distinguish
isolated tests from actions verified on a real network.

Preserve the MIT license notices and third-party attribution. See
[INSTALL.md](INSTALL.md), [capabilities](docs/CAPABILITIES.md) and the
[publication checklist](docs/PUBLISHING.md) for the supported scope.
