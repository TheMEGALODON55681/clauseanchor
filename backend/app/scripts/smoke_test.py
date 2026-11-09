"""CI smoke test: reviews a made-up PDF through a running API and checks what comes back.

    python backend/app/scripts/smoke_test.py http://127.0.0.1:8000

The image workflow runs it against the container before the image is published. It uses the
standard library only, so the runner needs nothing installed. The PDF is made up in this file, so
no contract text sits in the repository, in the image or in a log. Exit status 0 is a pass. A
failure prints the step that failed to stderr and exits 1. Development and CI only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any

# send(method, path, token=, body=, headers=) -> (status, headers, body). Status 0 is no answer.
Send = Callable[..., tuple[int, Mapping[str, str], bytes]]

LINES = (
    "SYNTHETIC SMOKE TEST DOCUMENT",
    "This page is made up for a pipeline check. It is not a contract.",
    "1. The parties are Alpha Testing Ltd and Beta Testing Ltd.",
    "2. This agreement is governed by the laws of the Republic of Testland.",
)
ENDED = {"succeeded", "partial", "failed", "cancelled", "timed_out"}


class SmokeFailure(Exception):
    """A step failed. The message names the step and holds no document text."""


def synthetic_pdf() -> bytes:
    """One page of Helvetica text, written by hand, with a correct cross-reference table."""
    text = "BT /F1 12 Tf 72 720 Td 18 TL " + " T* ".join(f"({line}) Tj" for line in LINES) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(text)} >>\nstream\n{text}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n{body}\nendobj\n".encode("ascii")
    entries = "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    size = len(objects) + 1
    trailer = f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{len(pdf)}\n%%EOF\n"
    return pdf + f"xref\n0 {size}\n0000000000 65535 f \n{entries}{trailer}".encode("ascii")


def check_analysis(analysis: Mapping[str, Any]) -> int:
    """Real mode, at least one window read by the model, and every finding a review candidate with
    no confidence and a model origin. Returns the number of findings. A review that finds nothing
    passes, because the model's reading of a made-up page is not something this script can promise.
    The window count is what shows that the model ran, and it also fails an empty category list."""
    if analysis.get("mode") != "real":
        raise SmokeFailure(f"mode: the analysis is {analysis.get('mode')!r}, not 'real'")
    if not any(category["windows_total"] for category in analysis["categories"]):
        raise SmokeFailure("windows: the model read no window of the page")
    count = 0
    for category in analysis["categories"]:
        for clause in category["clauses"]:
            for field, expected in (
                ("status", "review_candidate"),
                ("confidence", None),
                ("origin", "model"),
            ):
                if clause.get(field) != expected:
                    raise SmokeFailure(
                        f"{field}: a finding in {category['category_id']} has "
                        f"{clause.get(field)!r}, expected {expected!r}"
                    )
            count += 1
    return count


def _call(send: Send, step: str, method: str, path: str, expected: int, **request: Any) -> Any:
    """One request that must answer `expected`. Returns the JSON body, or None for no body."""
    status, _, body = send(method, path, **request)
    if status != expected:
        try:
            code = json.loads(body)["error"]["code"]
        except (ValueError, KeyError, TypeError):
            code = "no error code"
        raise SmokeFailure(f"{step}: {method} {path} answered {status} ({code})")
    return json.loads(body) if body else None


def _wait_ready(send: Send, timeout: float, interval: float) -> None:
    deadline = time.monotonic() + timeout
    last = "no answer"
    while True:
        status, _, body = send("GET", "/api/v1/ready")
        if status == 200:
            return
        if status:
            try:
                last = f"{status} {json.loads(body)['error']['details']['checks']}"
            except (ValueError, KeyError, TypeError):
                last = str(status)
        if time.monotonic() >= deadline:
            raise SmokeFailure(f"ready: not ready after {timeout:g} s (last answer: {last})")
        time.sleep(interval)


def _check_page(send: Send) -> None:
    status, _, page = send("GET", "/")
    if status != 200 or b'<div id="root"' not in page:
        raise SmokeFailure(f"app page: / answered {status} and did not serve the app")
    script = re.search(rb'src="(/assets/[^"]+\.js)"', page)
    if script is None:
        raise SmokeFailure("app page: index.html names no script under /assets/")
    path = script.group(1).decode("ascii")
    status, headers, _ = send("GET", path)
    kind = {name.lower(): value for name, value in headers.items()}.get("content-type", "")
    if status != 200 or "javascript" not in kind:
        raise SmokeFailure(f"app page: {path} answered {status} as {kind or 'no type'}")


def _wait_job(
    send: Send, step: str, token: str, job_id: str, timeout: float, interval: float
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        job = _call(send, step, "GET", f"/api/v1/jobs/{job_id}", 200, token=token)
        if job["status"] in ENDED:
            return job
        if time.monotonic() >= deadline:
            raise SmokeFailure(f"{step}: still {job['status']} after {timeout:g} s")
        time.sleep(interval)


def _why(job: Mapping[str, Any]) -> str:
    return f"the job {job['status']} ({(job['error'] or {}).get('code')})"


def smoke(
    send: Send, *, ready_timeout: float = 180.0, job_timeout: float = 300.0, interval: float = 1.0
) -> None:
    begun = time.monotonic()
    _wait_ready(send, ready_timeout, interval)
    print(f"ready after {time.monotonic() - begun:.0f} s", flush=True)
    _check_page(send)

    capabilities = _call(send, "capabilities", "GET", "/api/v1/capabilities", 200)
    if capabilities["mode"] != "real":
        raise SmokeFailure(f"mode: the analyzer is {capabilities['mode']!r}, not 'real'")
    category = next((c["id"] for c in capabilities["categories"] if c["source"] == "cuad"), None)
    if category is None:
        raise SmokeFailure("capabilities: the catalogue holds no CUAD category")

    token = _call(send, "session", "POST", "/api/v1/sessions", 201)["token"]
    upload = _call(
        send,
        "upload",
        "POST",
        "/api/v1/documents",
        202,
        token=token,
        body=synthetic_pdf(),
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": "attachment; filename*=UTF-8''smoke.pdf",
        },
    )
    parse = _wait_job(send, "parse", token, upload["parse_job_id"], job_timeout, interval)
    if parse["status"] != "succeeded":
        raise SmokeFailure(f"parse: {_why(parse)}")

    started = _call(
        send,
        "analysis",
        "POST",
        f"/api/v1/documents/{upload['document_id']}/analyses",
        202,
        token=token,
        body=json.dumps({"category_ids": [category], "jurisdiction_scope": "unspecified"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    job = _wait_job(send, "analysis", token, started["job_id"], job_timeout, interval)
    if job["status"] not in ("succeeded", "partial"):
        raise SmokeFailure(f"analysis: {_why(job)}")
    analysis = _call(
        send, "analysis", "GET", f"/api/v1/analyses/{started['analysis_id']}", 200, token=token
    )
    findings = check_analysis(analysis)
    print(
        f"analysis {job['status']}: {job['completed_units']} of {job['total_units']} units, "
        f"findings: {findings}",
        flush=True,
    )
    _call(send, "session", "DELETE", "/api/v1/sessions/current", 204, token=token)


def _http(base: str) -> Send:
    def send(method, path, *, token=None, body=None, headers=None):
        request = urllib.request.Request(
            base + path, data=body, method=method, headers=dict(headers or {})
        )
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()
        except OSError:  # the container is not listening yet
            return 0, {}, b""

    return send


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review a made-up PDF through a running API.")
    parser.add_argument("base_url", help="for example http://127.0.0.1:8000")
    args = parser.parse_args(argv)
    try:
        smoke(_http(args.base_url.rstrip("/")))
    except SmokeFailure as failure:
        print(f"FAIL {failure}", file=sys.stderr)
        return 1
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
