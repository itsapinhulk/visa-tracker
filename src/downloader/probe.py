"""Report how travel.state.gov answers this machine, method by method.

Whether a bulletin can be downloaded depends on where the request comes from as
much as how it is made: the same code that is served from one network is
refused from another. This asks for both forms of the same bulletin every way
the downloader knows, and prints what came back, so a refusal can be pinned on
the method or on the machine rather than guessed at.
"""

import dataclasses

import click
import requests
from curl_cffi import requests as curl_requests

from .HtmlSource import HtmlSource
from .PdfSource import PdfSource

_IMPERSONATIONS = ['chrome131', 'chrome124', 'chrome110', 'edge101', 'safari184']

_LISTING = "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"


def _describe(response) -> str:
  mitigated = response.headers.get('cf-mitigated')
  detail = f", cf-mitigated={mitigated}" if mitigated else ""
  return f"{response.status_code} ({len(response.content)} bytes{detail})"


@dataclasses.dataclass
class _Attempt:
  """One way of asking for a URL, ready to be tried."""
  name: str
  ask: object


def _attempts(url):
  yield _Attempt('plain requests', lambda: requests.get(url, timeout=60))

  for impersonation in _IMPERSONATIONS:
    yield _Attempt(f"curl_cffi {impersonation}",
                   lambda impersonation=impersonation:
                   curl_requests.get(url, impersonate=impersonation, timeout=60))

  def warmed():
    """A session that has been to the site before, carrying what it was given."""
    session = curl_requests.Session(impersonate='chrome131')
    try:
      session.get(_LISTING, timeout=60)
    except Exception:
      pass
    return session.get(url, timeout=60, headers={'Referer': _LISTING})

  yield _Attempt('curl_cffi chrome131, warmed session + referer', warmed)


@click.command()
@click.option('--year', type=int, required=True, help='Year of the bulletin to ask for.')
@click.option('--month', type=int, required=True, help='Month of the bulletin to ask for.')
def _main(year, month):
  import datetime
  target = datetime.date(year, month, 1)

  for source_cls in (HtmlSource, PdfSource):
    url = source_cls(target, None).url()
    print(f"\n{source_cls.__name__}: {url}")

    for attempt in _attempts(url):
      try:
        print(f"  {attempt.name:<44} {_describe(attempt.ask())}")
      except Exception as error:
        print(f"  {attempt.name:<44} failed: {type(error).__name__}: {str(error)[:60]}")


if __name__ == '__main__':
  _main()
