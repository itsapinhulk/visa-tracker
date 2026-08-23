from __future__ import annotations

import time

import requests
from curl_cffi import requests as curl_requests

_TURNSTILE_HOST = "challenges.cloudflare.com"

# Chrome build whose TLS fingerprint curl_cffi presents. travel.state.gov
# bot-scores the raw fingerprint, so a plain `requests` GET is refused where an
# identical request carrying a real browser's fingerprint is served.
_IMPERSONATE = "chrome131"

# Smallest gap between two requests, whichever method makes them. Paces every
# request rather than every month: one month can take several attempts.
_REQUEST_INTERVAL_S = 0.1
_last_request = 0.0


def _pace():
  """Hold off until _REQUEST_INTERVAL_S has passed since the last request."""
  global _last_request

  wait = _last_request + _REQUEST_INTERVAL_S - time.monotonic()
  if wait > 0:
    time.sleep(wait)
  _last_request = time.monotonic()


class Fetcher:
  """How to pull a URL down off the wire.

  Independent of what is being fetched -- an HTML page and a PDF are retrieved
  the same way -- so sources say *what* to fetch and a Fetcher says *how*.
  """

  def fetch(self, url: str) -> tuple[int | None, bytes]:
    """Retrieve url. Returns (status, content).

    Every fetcher returns the document as the raw bytes it was served as, so
    which one retrieved a URL never changes what gets cached.

    A status of None means the fetcher decided this URL should be skipped
    rather than treated as a failure; the caller reports it as not downloaded
    instead of raising.
    """
    raise NotImplementedError


class RequestsFetcher(Fetcher):
  """A plain HTTP GET."""

  def fetch(self, url: str) -> tuple[int | None, bytes]:
    print(f"Downloading {url} with a plain HTTP request")
    _pace()
    resp = requests.get(url)
    return resp.status_code, resp.content


class ImpersonatingFetcher(Fetcher):
  """A GET carrying a real browser's TLS fingerprint.

  Enough to get past bot scoring that refuses a plain request, but not enough
  to pass an interactive Cloudflare challenge -- that needs BrowserFetcher.
  """

  def fetch(self, url: str) -> tuple[int | None, bytes]:
    print(f"Downloading {url} with a {_IMPERSONATE} TLS fingerprint")
    _pace()
    resp = curl_requests.get(url, impersonate=_IMPERSONATE)
    return resp.status_code, resp.content


class BrowserFetcher(Fetcher):
  """A GET driven through a real browser, clearing a Cloudflare challenge.

  The browser hands back a parsed document rather than the bytes off the wire,
  so this is the one method that re-serializes; travel.state.gov serves UTF-8,
  which is what the other fetchers come back with too.
  """

  def fetch(self, url: str) -> tuple[int | None, bytes]:
    _pace()
    status, html = browserFetch(url)
    return status, html.encode("utf-8")


class ChainFetcher(Fetcher):
  """Try each fetcher in turn until one of them gets the document.

  travel.state.gov answers differently depending on how it is asked, so a
  refusal from one method says nothing about the next. A 404 is taken as the
  site's final word and stops the chain; anything else that failed just moves
  on to the next method.
  """

  def __init__(self, fetchers: list[Fetcher], ignore_failure: bool = False):
    # Every method may still be refused (e.g. from a flagged datacenter IP).
    # With ignore_failure, skip instead of failing the whole run so any pages
    # that did succeed still go through.
    self.fetchers = fetchers
    self.ignore_failure = ignore_failure

  def fetch(self, url: str) -> tuple[int | None, bytes]:
    status, content = None, b""

    for index, fetcher in enumerate(self.fetchers):
      status, content = fetcher.fetch(url)

      if status == 200 or status == 404:
        return status, content

      if index + 1 < len(self.fetchers):
        print(f"Got {status} for {url}, retrying")
      else:
        print(f"Got {status} for {url}")

    if self.ignore_failure:
      print(f"Skipping {url} (no download method could retrieve it)")
      return None, b""

    return status, content


def browserFetch(url: str, timeout_s: int = 90) -> tuple[int, str]:
  """Fetch a Cloudflare-protected page with a real browser.

  travel.state.gov sits behind a Cloudflare "Verify you are human" (Turnstile)
  challenge that a plain HTTP request cannot pass -- it returns a 403 challenge
  page regardless of headers or User-Agent. We drive a headed Chromium (via
  patchright) and click the Turnstile checkbox to clear the challenge. On a
  headless server run this under a virtual display, e.g. `xvfb-run` (see
  update_data.sh); pure headless mode gets hard-blocked.

  Returns (status, html): 200 with the page HTML on success, or 404 when the
  page does not exist (used with --ignore_404 to probe future months).
  """
  print(f"Downloading {url} with a headed browser")

  from patchright.sync_api import sync_playwright

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
    try:
      page = browser.new_context(
          viewport={"width": 1000, "height": 800}, locale="en-US").new_page()

      # Track the status of the main-document navigations for this URL. A
      # missing page resolves 307 -> 403 (challenge) -> 404 once cleared.
      doc_status = {"code": None}
      def _track(resp):
        if resp.url.split("?")[0] == url and resp.request.resource_type == "document":
          doc_status["code"] = resp.status
      page.on("response", _track)

      page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)

      deadline = time.time() + timeout_s
      while time.time() < deadline:
        title = page.title().lower()
        html = page.content()

        # Real page has loaded (challenge cleared, tables present).
        if "just a moment" not in title and "<table" in html.lower():
          return 200, html
        # Page does not exist (e.g. probing a not-yet-published month).
        if doc_status["code"] == 404 or "page not found" in title:
          return 404, html

        # Click the Turnstile checkbox if the challenge is showing.
        for frame in page.frames:
          if _TURNSTILE_HOST in frame.url:
            box = frame.query_selector("input[type=checkbox]")
            if box is not None:
              try:
                box.click()
              except Exception:
                pass
        time.sleep(1.5)

      # Challenge never cleared within the timeout. Return the last document
      # status (typically 403) so the caller can decide whether to fail or skip.
      print(f"Timed out clearing Cloudflare challenge for {url} "
            f"(last document status {doc_status['code']})")
      return doc_status["code"] or 403, page.content()
    finally:
      browser.close()
