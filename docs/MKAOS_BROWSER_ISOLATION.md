# Isolated Playwright browser lab

This is a first-stage screenshot-only worker for the included local fixture, not a general
web scanner. It exposes navigation and screenshot capture only; it does not expose click,
form-submit, JavaScript-evaluation, download, credential, exploit, or destructive tools.

## Run locally

    mkdir -p artifacts/browser
    docker compose -f docker-compose.browser.yml --profile browser-lab build browser-worker
    docker compose -f docker-compose.browser.yml --profile browser-lab run --rm browser-worker \
      --url http://browser-fixture:80/ --output /screenshots/fixture.png

The Compose network is internal-only, has no published host ports, and contains only the
fixture and worker. The worker runs non-root, with a read-only root filesystem, dropped
Linux capabilities, no-new-privileges, memory/CPU/PID limits, no Docker socket, and no
application credentials. Screenshots are the only writable host-mounted output. The worker
checks exact hostname and port allowlists, rejects public/reserved target addresses, and rechecks each browser request, including redirects and subresources.

## Security limits and next gates

- The default allowlist is only browser-fixture; do not add production or public hosts.
- Keep the internal network and do not attach the worker to the application's general
  network. This initial compose file is a local lab, not a production scanner.
- Pin the Playwright base image to a reviewed immutable digest before production use.
- Test DNS rebinding, redirects, IPv4/IPv6, unusual ports, timeouts, memory exhaustion,
  browser escapes, and artifact permissions before broadening scope.
- Live scanning and any browser interactions beyond navigation/screenshot require an
  explicit human approval and a separately reviewed allowlist. Never mount credentials
  or the host Docker socket into the browser worker.
