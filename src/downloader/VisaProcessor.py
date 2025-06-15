import csv
import datetime
import pathlib
import time

from .Data import Data, DataEntry


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
    if data.download():
      time.sleep(0.1)

  for data in all_data:
    print(f"Processing data for {data.year}/{data.month}")
    [field_names, csv_data] = _convertToCsv(all_entries=data.extract())

    yearDir = data_dir / f"{data.year}"
    yearDir.mkdir(parents=True, exist_ok=True)
    filePath = yearDir / f"{data.month:02d}_{Data.MONTH_TO_STR[data.month]}.csv"
    with open(filePath, 'w', newline='') as csvfile:
      writer = csv.DictWriter(csvfile, delimiter=',', lineterminator='\n',
                              quotechar='|', quoting=csv.QUOTE_MINIMAL,
                              fieldnames=field_names)
      writer.writeheader()
      writer.writerows(csv_data)


def _convertToCsv(all_entries: list[DataEntry]):
  values_l1 = {} # country -> category -> [filing_date, final_action_date}

  for entry in all_entries:
    if entry.year not in values_l1 :
      values_l1[entry.year] = {}

    year_entry = values_l1[entry.year]
    if entry.month not in year_entry:
      values_l1[entry.year][entry.month] = {}

    month_entry = values_l1[entry.year][entry.month]
    if entry.country not in month_entry:
      values_l1[entry.year][entry.month][entry.country] = {}

    country_entry = values_l1[entry.year][entry.month][entry.country]

    if entry.visa_type not in country_entry:
      values_l1[entry.year][entry.month][entry.country][entry.visa_type] = {
        'final_action_date': None,
        'filing_date': None,
      }

    category_entry = values_l1[entry.year][entry.month][entry.country][entry.visa_type]
    if entry.is_final_action_date :
      category_entry['final_action_date'] = entry.date
    else :
      category_entry['filing_date'] = entry.date

  field_names = [
    'year',
    'month',
    'country',
    'category',
    'final_action_date',
    'filing_date',
  ]

  values = []

  for year, year_entries in values_l1.items():
    for month, month_entries in year_entries.items() :
      for country, country_entries in month_entries.items() :
        for category, category_entry in country_entries.items() :
          values.append({
            'year': year,
            'month': month,
            'country': country.value,
            'category': category.value,
            'final_action_date': category_entry['final_action_date'],
            'filing_date': category_entry['filing_date'],
          })

  return field_names, values
