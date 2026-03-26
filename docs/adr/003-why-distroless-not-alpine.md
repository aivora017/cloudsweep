# ADR 003 — Why distroless base image, not Alpine

**Date:** 2026-03-26
**Status:** Accepted

---

## Context

The CloudSweep scanner Docker image needs a Python 3.11 runtime. Common
choices for minimal base images are:

1. **`gcr.io/distroless/python3-debian12:nonroot`** (Google distroless)
2. **`python:3.11-alpine`**
3. **`python:3.11-slim`** (Debian slim — used as build stage)

## Decision

Use distroless (`gcr.io/distroless/python3-debian12:nonroot`) as the final
runtime image in the multi-stage build.

## Reasons

### Attack surface
Distroless images contain *only* the application and its runtime dependencies:
no shell, no package manager, no coreutils, no `curl`, no `wget`. Alpine
includes `busybox`, a shell, `apk`, and a full POSIX userland.

If an attacker exploits a vulnerability in the scanner's Python dependencies
and achieves code execution, they cannot:
- Install additional tools (`apk add`, `apt-get`)
- Run shell commands directly
- Use `/bin/sh` or `/bin/bash` for lateral movement

### CVE surface
Trivy scans (added in `pr-checks.yml`) consistently find fewer CRITICAL/HIGH
CVEs in distroless images than in Alpine, because there are fewer packages to
have vulnerabilities. In practice, Alpine's musl libc has historically had
fewer CVEs than glibc, but the total package count in distroless is far lower.

### `nonroot` user by default
The `:nonroot` tag runs the process as UID 65532 (nobody). Alpine images
default to root unless you explicitly add `USER` instructions.

### Trivy integration
The CI Trivy step (`aquasecurity/trivy-action`) fails PRs with CRITICAL/HIGH
CVEs. Distroless makes it substantially easier to keep a clean scan result
over time without regularly chasing CVE fixes in Alpine packages we don't
control.

## Trade-offs accepted

- **No shell for debugging:** `kubectl exec` into a running container yields
  nothing useful. For debugging, use `kubectl logs` or add a debug sidecar.
  This is acceptable because the scanner is a batch job that writes structured
  logs to stdout.
- **Larger image size than Alpine:** Distroless Debian12 is ~50 MB versus
  Alpine ~10 MB. The multi-stage build keeps the final layer lean (no build
  tools), so the practical difference is <20 MB — acceptable given the image
  is pulled once per weekly scan run.
- **No `pip` in runtime image:** All Python packages must be installed during
  the build stage. This is enforced by the Dockerfile's multi-stage structure
  and prevents accidental runtime installs.

## Consequences

- The `Dockerfile` uses `python:3.11-slim` as the build stage and
  `gcr.io/distroless/python3-debian12:nonroot` as the runtime stage.
- `PYTHONPATH` must be explicitly set to point at the venv's site-packages
  since distroless has no activation mechanism.
- Any debugging of the scanner container must be done via logs or a
  temporary debug sidecar; `kubectl exec -it ... -- /bin/sh` will fail.
