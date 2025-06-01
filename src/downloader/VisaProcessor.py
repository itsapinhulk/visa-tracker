import datetime
import pathlib
import time

from .Data import Data

def processDates(*, start_date: datetime.date, end_date: datetime.date,
                 cache_dir: pathlib.Path, data_dir: pathlib.Path):
  # Figure out all the dates we need to process
  all_dates = []
  curr_date = datetime.date(year=start_date.year, month=start_date.month, day=1)

  start_str = f"{start_date.year}/{start_date.strftime("%m")}-{start_date.strftime('%B')}"
  end_str = f"{end_date.year}/{end_date.strftime('%m')}-{end_date.strftime('%B')}"
  print(f"Processing dates from {start_str} to {end_str}")
  while curr_date <= end_date:
    all_dates.append(curr_date)

    # Jump to next month
    curr_date += datetime.timedelta(days=35)

    # Always pick first day to avoid ambiguity
    curr_date = datetime.date(year=curr_date.year, month=curr_date.month, day=1)

  all_data = []
  for curr_date in all_dates:
    cache_year = cache_dir / curr_date.strftime("%Y")
    cache_year.mkdir(parents=True, exist_ok=True)
    cache_file = cache_year / curr_date.strftime("%m_%B.html")
    data = Data(curr_date, cache_file)
    all_data.append(data)

  for data in all_data:
    if data.download() :
      time.sleep(0.1)
