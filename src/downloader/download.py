import datetime
import pathlib

import click

from .HtmlSource import HtmlSource
from .Http import BrowserFetcher, ChainFetcher, ImpersonatingFetcher, RequestsFetcher
from .PdfSource import PdfSource
from .VisaProcessor import processDates

# Preference order for --any-source. HTML first because it is the only form
# anything knows how to read; the PDF is the more reliable download.
_ANY_SOURCE_ORDER = [HtmlSource, PdfSource]

_SupportedDateInputs = click.DateTime(formats=['%Y-%m', '%Y%m'])

@click.command()
@click.option('--cache_dir', type=click.Path(exists=True), required=True,
              help='Directory to store downloaded files.')
@click.option('--data_dir', type=click.Path(exists=True), required=True,
              help='Directory to store downloaded files.')
@click.option('--start_date', type=_SupportedDateInputs,
              help='Start date of the download in YYYY-MM-DD format.')
@click.option('--end_date', type=_SupportedDateInputs,
              help='End date of the download in YYYY-MM-DD format.')
@click.option('--ignore_404', is_flag=True, default=False,
              help='Skip pages that return a 404 instead of raising an error.')
@click.option('--aggressive', is_flag=True, default=False,
              help='Always query the next month regardless of current day.')
@click.option('--ignore-cached', is_flag=True, default=False,
              help='Download every bulletin again, ignoring the cache.')
@click.option('--html', 'html', is_flag=True, default=False,
              help='Read the bulletin from the HTML page (the default).')
@click.option('--pdf', 'pdf', is_flag=True, default=False,
              help='Read the bulletin from the PDF.')
@click.option('--any-source', 'any_source', is_flag=True, default=False,
              help='Try each form of the bulletin in turn, using whichever one '
                   'the site will hand over.')
@click.option('--fallback', is_flag=True, default=False,
              help='On a 403 (Cloudflare challenge), retry via a real browser. '
                   'Requires patchright + a browser (see update_data.sh).')
@click.option('--ignore-fallback-failure', is_flag=True, default=False,
              help='If no download method can retrieve a page, skip it instead '
                   'of failing the run.')
def _main(cache_dir, data_dir, start_date = None, end_date = None, ignore_404 = False,
          aggressive = False, ignore_cached = False, html = False, pdf = False,
          any_source = False, fallback = False, ignore_fallback_failure = False):
  if sum([html, pdf, any_source]) > 1:
    raise click.UsageError('--html, --pdf and --any-source are mutually exclusive.')

  cache_dir = pathlib.Path(cache_dir).absolute()
  data_dir = pathlib.Path(data_dir).absolute()

  if end_date is None:
    end_date = datetime.date.today()
    # Choose next month after the 15th, or always in aggressive mode
    if aggressive or end_date.day >= 15:
      end_date += datetime.timedelta(days=20)
      end_date = end_date.replace(day=1)
  else :
    end_date = end_date.date()

  if start_date is None:
    # Set it to one month before the end date
    start_date = end_date
    start_date = start_date.replace(day=1)
    start_date -= datetime.timedelta(days=2)
    start_date = start_date.replace(day=1)
  else :
    start_date = start_date.date()

  EARLIEST_START_DATE = datetime.date(year=2001, month=12, day=1)
  if start_date < EARLIEST_START_DATE:
    raise Exception("Start date must be at least 2001-12-December")


  # Each method is tried in turn: travel.state.gov refuses a plain request but
  # serves the same URL to a browser TLS fingerprint, and hides other pages
  # behind a challenge only a real browser clears.
  fetchers = [RequestsFetcher(), ImpersonatingFetcher()]
  if fallback:
    fetchers.append(BrowserFetcher())
  fetcher = ChainFetcher(fetchers, ignore_failure=ignore_fallback_failure)

  if pdf:
    source_classes = [PdfSource]
  elif any_source:
    source_classes = _ANY_SOURCE_ORDER
  else:
    source_classes = [HtmlSource]

  processDates(start_date=start_date, end_date=end_date, cache_dir=cache_dir, data_dir=data_dir,
               source_classes=source_classes, fetcher=fetcher, ignore_404=ignore_404,
               ignore_cached=ignore_cached)

if __name__ == '__main__':
    _main()
