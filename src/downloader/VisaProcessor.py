import csv
import dataclasses
import datetime
import enum
import pathlib

from .Data import MONTH_TO_STR, DataEntry, Source, VisaCategory, CountryCategory
from .Http import Fetcher


class Outcome(enum.Enum):
  """How a month turned out."""
  DOWNLOADED = 'downloaded'
  UNPUBLISHED = 'not published yet'
  REFUSED = 'refused'


@dataclasses.dataclass
class Resolved:
  """The source a month will be read from, or why there is none.

  A bulletin not published yet reads very differently from one the site would
  not hand over, so which it was travels with the answer.
  """
  source: Source | None
  outcome: Outcome


@dataclasses.dataclass
class CsvData:
  """The stored form of a month: its column names and its rows."""
  field_names: list[str]
  rows: list[dict]


def processDates(*, start_date: datetime.date, end_date: datetime.date,
                 cache_dir: pathlib.Path, data_dir: pathlib.Path,
                 source_classes: list[type[Source]], fetcher: Fetcher,
                 ignore_404: bool = False, ignore_cached: bool = False):
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
  skipped = {}
  for curr_date in all_dates:
    cache_year = cache_dir / curr_date.strftime("%Y")
    cache_year.mkdir(parents=True, exist_ok=True)
    sources = [cls(curr_date, cache_year / (curr_date.strftime("%m_%B") + cls.CACHE_SUFFIX))
               for cls in source_classes]

    resolved = _firstAvailable(sources, fetcher=fetcher, ignore_404=ignore_404,
                               ignore_cached=ignore_cached)
    if resolved.source is not None:
      all_data.append(resolved.source)
    else:
      skipped[resolved.outcome] = skipped.get(resolved.outcome, 0) + 1

  summary = "".join(f", {count} {outcome.value}" for outcome, count in skipped.items())
  print(f"Downloaded {len(all_data)} of {len(all_dates)} months{summary}")

  if not all_data and skipped.get(Outcome.REFUSED):
    # Every month was refused. Skipping them all and reporting success would
    # leave a scheduled run looking healthy while it quietly stopped working.
    raise Exception("Nothing could be downloaded: every month was refused")

  for data in all_data:
    print(f"Processing data for {data.year}/{data.month}")
    converted = _convertToCsv(all_entries=data.extract())

    yearDir = data_dir / f"{data.year}"
    yearDir.mkdir(parents=True, exist_ok=True)
    filePath = yearDir / f"{data.month:02d}_{MONTH_TO_STR[data.month]}.csv"
    with open(filePath, 'w', newline='') as csvfile:
      writer = csv.DictWriter(csvfile, delimiter=',', lineterminator='\n',
                              quotechar='|', quoting=csv.QUOTE_MINIMAL,
                              fieldnames=converted.field_names)
      writer.writeheader()
      writer.writerows(converted.rows)


def _firstAvailable(sources: list[Source], *, fetcher: Fetcher, ignore_404: bool,
                    ignore_cached: bool = False) -> Resolved:
  """Settle on the first source this month can actually be read from.

  A source already in the cache is used as-is. Otherwise travel.state.gov is
  asked for it -- and since the site does not serve every form of a bulletin
  the same way (one may sit behind a challenge, or not be published at all), a
  refusal for one form says nothing about the next, so each is tried before a
  month is given up on. Sources are considered in preference order, so a
  preferred source is downloaded rather than falling back to a cached lesser
  one. Returns None when the month should be skipped.
  """
  statuses = []

  for source in sources:
    if not ignore_cached and source.path.exists():
      print(f"Skipping download {source.url()}")
      return Resolved(source, Outcome.DOWNLOADED)

    status = source.download(fetcher)
    statuses.append(status)

    if status == 200:
      return Resolved(source, Outcome.DOWNLOADED)

  month = f"{sources[0].year}/{sources[0].month}"

  if all(status == 404 for status in statuses):
    if ignore_404:
      print(f"Skipping data for {month} (404)")
      return Resolved(None, Outcome.UNPUBLISHED)
  elif None in statuses:
    # A fetcher gave up rather than fail the run (--ignore-fallback-failure).
    print(f"Skipping data for {month} (could not be downloaded)")
    return Resolved(None, Outcome.REFUSED)

  detail = ", ".join(f"{type(source).__name__} got {status}"
                     for source, status in zip(sources, statuses))
  raise Exception(f"Failed to download {month}: {detail}")


def _convertToCsv(all_entries: list[DataEntry]) -> CsvData:
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

    if (entry.year == 2001 or entry.year == 2002) and \
            (entry.month == 12 or entry.month <= 2) and \
            (entry.visa_type == VisaCategory.F4) and \
            (entry.country == CountryCategory.PHILIPPINES) and \
            (entry.date >= datetime.date(2079, 10, 31)):
        # Very wrong dates for this combination
        entry.date = None
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

  return CsvData(field_names=field_names, rows=values)
