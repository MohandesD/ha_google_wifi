# Testing and release verification

Tests require Python 3.14 and Node.js 24. Use an isolated development environment:

```sh
python -m venv .venv
# Activate the environment, then:
python -m pip install -r requirements-dev.txt
npm ci --ignore-scripts
python -m ruff check --select F,E9,I custom_components tests tools
python -m pytest -q --cov --cov-report=term-missing --cov-report=json --cov-fail-under=90
npm test
python tools/sync_frontend.py --check
python tools/build_package.py
python tools/validate_release.py
```

The Python suite blocks non-loopback HTTP in both aiohttp and requests. Real
transport tests use ephemeral loopback servers. HA fixtures use temporary config
directories, fictional accounts and mocked Google discovery; no household config,
tokens, browser storage or LAN capture is needed. The 100/300-client tests write
only aggregate `scale-metrics.json` files into their temporary directories.

With `--basetemp=test-runtime-ci`, CI retains those scale files together with
coverage reports. Peak Python allocations exclude the rest of the HA process;
the tests do not start Recorder or estimate actual database growth. Timings depend
on the host and coverage instrumentation and are observations, not service SLAs.

CI runs a pinned minimum HA/frontend environment and another job upgrading to the
latest release. It also runs HACS/hassfest, Python runtime dependency auditing and
`npm audit`. No failed check is marked successful by ignoring its outcome. Local
brand assets satisfy the HACS branding check; default-catalogue submission is separate.

Naming concurrency tests use event barriers rather than timing-based speed claims.
They verify three overlapping client operations, durable per-client intent,
same-client duplicate prevention, network-action fairness, cancellation cleanup
and shared HTTP 429 cooldowns. Frontend tests exercise bounded groups, late and
out-of-order replies, stop/failure behavior, cached refresh failures and older
backend compatibility. These checks do not measure live Google throughput.

The archive uses fixed timestamps, stable permissions, sorted members and LF text.
The verifier checks versions, translations, mirrored UI, archive/source identity,
unexpected members and common credential patterns. A release still requires a
human review of the diff and public-file selection. Pattern checks cannot establish
that arbitrary personal data is absent.

Run any remaining live onboarding, compatibility or destructive-action validation
only in a separate explicitly authorized lab. Record those results in the
[readiness matrix](RELEASE_READINESS.md), distinguishing observation from inference.

## Browser demo

Run `python tools/demo_server.py` and open
`http://127.0.0.1:8876/tools/demo.html`. It serves only the public UI and fictional
fixtures on loopback. Its content policy blocks provider/API connections and its
service interface returns local fixture data. No real HA instance or Google
account is connected, and network actions are disabled.

The demo imports the released panel modules directly; it does not redraw the
dashboard. A simulated Home Assistant frame provides ordinary sidebar context,
Roboto typography and demo-only Material Design icons. These assets are local;
see [credits](../CREDITS.md) for their licenses.

Use the language/scenario selectors at the bottom, Overview/Map/Management/Locations tabs,
information disclosures and history controls to check desktop/mobile layout, missing signal and partial
network failure. Fixture updates arrive every three seconds for scroll/focus
regression checks. Stop the server with Ctrl+C. README screenshots are taken from
this demo, never from a private installation.

For screenshot capture, use `?capture=1` to hide the demo controls and stop the
three-second fixture updates. Start at `&view=map` or `&view=management` to open
those views directly; use `&view=locations&scenario=homes` for two fictional cloud
homes and a separate local-status entry. Its location saves change only fixture
objects. The default is Overview. Wait for **24 connected clients**
or the populated management controls before capturing. Use ordinary viewport
captures and scroll to individual sections rather than shrinking a whole long
page into an unreadable image. The small demo badge, generic demo user, names,
documentation-only IP ranges and locally administered MACs distinguish this
fixture from a real installation. See [screenshot provenance](images/README.md).

Use `&scenario=stress` for long point labels, `&language=pt` for Portuguese and
`&theme=dark` for the dark fixture. Theme and scenario controls are also available
outside capture mode. Check Overview, Map, Management and Locations at 320, 768
and 1280 pixels: the document must fit its viewport, controls must remain usable,
and Management must expose exactly one explicit cloud-network selector. Confirm
that unavailable or local-only homes cannot silently target another home's cloud
network. These are layout checks with fictional data, not live household trials.
The [narrow-screen capture](images/management-mobile-demo.png) shows the expected
tab and filter layout without horizontal page scrolling.

The fictional Management view also supports `set_client_area_sync` locally.
Verify that checking **Automatically follow Wi-Fi Point areas** and saving keeps
the selected state, without enabling **Also move matching Home Assistant devices**
or automatic naming. Check the new controls at 320, 768 and 1280 pixels in English
and Portuguese/dark mode. No real HA registry or device area is changed by the demo.
