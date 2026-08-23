from __future__ import annotations

import time

import requests

_TURNSTILE_HOST = "challenges.cloudflare.com"


class Fetcher:
  """How to pull a URL down off the wire.

  Independent of what is being fetched -- an HTML page and a PDF are retrieved
  the same way -- so sources say *what* to fetch and a Fetcher says *how*.
  """

  def fetch(self, url: str) -> tuple[int | None, bytes]:
    """Retrieve url. Returns (status, content).

    A status of None means the fetcher decided this URL should be skipped
    rather than treated as a failure; the caller reports it as not downloaded
    instead of raising.
    """
    raise NotImplementedError


class RequestsFetcher(Fetcher):
  """A plain HTTP GET."""

  def fetch(self, url: str) -> tuple[int | None, bytes]:
    resp = requests.get(url)
    return resp.status_code, resp.text.encode("utf-8")


class BrowserFallbackFetcher(Fetcher):
  """A plain GET, falling back to a real browser on a Cloudflare challenge.

  travel.state.gov hides pages behind a Cloudflare "Verify you are human"
  (Turnstile) challenge, which answers a plain request with 403. The browser
  clears it; see browserFetch.
  """

  def __init__(self, ignore_failure: bool = False):
    # The browser may still fail to clear the challenge (e.g. from a flagged
    # datacenter IP). With ignore_failure, skip instead of failing the whole
    # run so any pages that did succeed still go through.
    self.ignore_failure = ignore_failure

  def fetch(self, url: str) -> tuple[int | None, bytes]:
    status, content = RequestsFetcher().fetch(url)
    if status != 403:
      return status, content

    print(f"Got 403 for {url}; retrying with browser fallback")
    status, html = browserFetch(url)
    if status == 403 and self.ignore_failure:
      print(f"Skipping {url} (browser fallback could not clear the challenge)")
      return None, b""

    return status, html.encode("utf-8")


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
