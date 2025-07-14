import datetime
import pathlib

import click

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
def _main(cache_dir, data_dir, start_date = None, end_date = None):
  cache_dir = pathlib.Path(cache_dir).absolute()
  data_dir = pathlib.Path(data_dir).absolute()

  if end_date is None:
    end_date = datetime.date.today()
    # Choose next month after the 15th
    if end_date.day >= 15:
      end_date += datetime.timedelta(days=20)
      end_date = end_date.replace(day=1)
  else :
    end_date = end_date.date()

  if start_date is None:
    # Set it to one month before end date
    start_date = end_date
    start_date = start_date.replace(day=1)
    start_date -= datetime.timedelta(days=2)
    start_date = start_date.replace(day=1)
  else :
    start_date = start_date.date()

  EARLIEST_START_DATE = datetime.date(year=2001, month=12, day=1)
  if start_date < EARLIEST_START_DATE:
    raise Exception("Start date must be at least 2001-12-December")


  processDates(start_date=start_date, end_date=end_date, cache_dir=cache_dir, data_dir=data_dir)

if __name__ == '__main__':
    _main()
