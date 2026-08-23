import datetime
import pathlib

import click

from .HtmlSource import HtmlSource
from .Http import BrowserFallbackFetcher, RequestsFetcher
from .VisaProcessor import processDates

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
@click.option('--fallback', is_flag=True, default=False,
              help='On a 403 (Cloudflare challenge), retry via a real browser. '
                   'Requires patchright + a browser (see update_data.sh).')
@click.option('--ignore-fallback-failure', is_flag=True, default=False,
              help='If the browser fallback still gets a 403 (challenge not '
                   'cleared), skip that page instead of failing the run.')
def _main(cache_dir, data_dir, start_date = None, end_date = None, ignore_404 = False,
          aggressive = False, fallback = False, ignore_fallback_failure = False):
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


  if fallback:
    fetcher = BrowserFallbackFetcher(ignore_failure=ignore_fallback_failure)
  else:
    fetcher = RequestsFetcher()

  processDates(start_date=start_date, end_date=end_date, cache_dir=cache_dir, data_dir=data_dir,
               source_cls=HtmlSource, fetcher=fetcher, ignore_404=ignore_404)

if __name__ == '__main__':
    _main()
