"""Check the stored CSVs against what each source produces today.

The data in data/ was built from whichever source was reachable at the time.
This re-derives it from every source and compares, so that a source drifting --
a layout the parser no longer reads the same way, a bulletin republished with
different dates -- shows up as a difference rather than going unnoticed until
it lands in a data update.
"""

import csv
import dataclasses
import datetime
import pathlib

import click

from .Data import MONTH_TO_STR, Source
from .HtmlSource import HtmlSource
from .Http import IMPERSONATIONS, BrowserFetcher, ChainFetcher, ImpersonatingFetcher, RequestsFetcher
from .PdfSource import PdfSource
from .VisaProcessor import _convertToCsv

SOURCES = {
  'html': HtmlSource,
  'pdf': PdfSource,
}

_SupportedDateInputs = click.DateTime(formats=['%Y-%m', '%Y%m'])

# How far back to check when no range is asked for. Every stored month is a few
# hundred downloads; the recent ones are where drift would show up first.
_DEFAULT_MONTHS = 3


@dataclasses.dataclass
class _Dates:
  """The pair of cut-off dates stored for one country and category."""
  final_action: str
  filing: str

  def field(self, name: str) -> str:
    return self.final_action if name == 'final_action_date' else self.filing


@dataclasses.dataclass
class _Mismatch:
  """One place the stored data and the recomputed data disagree."""
  country: str
  category: str
  field: str
  stored: str
  computed: str


@dataclasses.dataclass
class _Outcome:
  """What checking one month against one source came to."""
  month: datetime.date
  source: str
  status: str
  mismatches: list = dataclasses.field(default_factory=list)

  @property
  def failed(self):
    return self.status != 'ok'


def _storedMonths(data_dir: pathlib.Path):
  months = []
  for path in sorted(data_dir.glob("*/*.csv")):
    year = int(path.parent.name)
    month = int(path.name.split("_")[0])
    months.append(datetime.date(year, month, 1))
  return months


def _readStored(path: pathlib.Path):
  rows = {}
  with open(path, newline='') as stored:
    for row in csv.DictReader(stored):
      rows[(row['country'], row['category'])] = _Dates(
        final_action=row['final_action_date'] or '', filing=row['filing_date'] or '')
  return rows


def _computed(source: Source):
  converted = _convertToCsv(all_entries=source.extract())
  return {(value['country'], value['category']):
          _Dates(final_action=str(value['final_action_date'] or ''),
                 filing=str(value['filing_date'] or ''))
          for value in converted.rows}


_FIELDS = ['final_action_date', 'filing_date']


def _compare(stored, computed) -> list[_Mismatch]:
  """Every place the two disagree."""
  mismatches = []

  for key in sorted(set(stored) | set(computed), key=str):
    country, category = key
    if key not in computed:
      mismatches.append(_Mismatch(country, category, 'row', 'present', 'missing'))
      continue
    if key not in stored:
      mismatches.append(_Mismatch(country, category, 'row', 'missing', 'present'))
      continue

    for field in _FIELDS:
      was, now = stored[key].field(field), computed[key].field(field)
      if was != now:
        mismatches.append(_Mismatch(country, category, field, was or '-', now or '-'))

  return mismatches


def _check(source_name, target, cache_dir, data_dir, fetcher, ignore_cached):
  source_cls = SOURCES[source_name]
  # The same cache the downloader fills, laid out the same way. The two forms
  # of a bulletin differ by file extension, so they sit alongside each other.
  cache_year = cache_dir / target.strftime("%Y")
  cache_year.mkdir(parents=True, exist_ok=True)
  source = source_cls(target,
                      cache_year / (target.strftime("%m_%B") + source_cls.CACHE_SUFFIX))

  if ignore_cached or not source.path.exists():
    try:
      status = source.download(fetcher)
    except Exception as error:
      return _Outcome(target, source_name, f"download failed: {error}")
    if status != 200:
      return _Outcome(target, source_name, f"download failed: got {status}")

  try:
    computed = _computed(source)
  except Exception as error:
    return _Outcome(target, source_name, f"could not read: {error}")

  stored_path = data_dir / f"{target.year}" / f"{target.month:02d}_{MONTH_TO_STR[target.month]}.csv"
  mismatches = _compare(_readStored(stored_path), computed)

  return _Outcome(target, source_name, 'ok' if not mismatches else 'mismatch', mismatches)


def _printTable(headers, rows):
  if not rows:
    return

  widths = [max(len(str(row[index])) for row in [headers] + rows)
            for index in range(len(headers))]
  line = "  ".join(str(headers[i]).ljust(widths[i]) for i in range(len(headers)))
  print(f"  {line.rstrip()}")
  print(f"  {'  '.join('-' * width for width in widths)}")

  for row in rows:
    line = "  ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers)))
    print(f"  {line.rstrip()}")


def _report(outcomes, source_names):
  by_month = {}
  for outcome in outcomes:
    by_month.setdefault(outcome.month, {})[outcome.source] = outcome

  print("\nPer month, per source\n")
  rows = []
  for month in sorted(by_month):
    row = [month.strftime("%Y-%m")]
    for name in source_names:
      outcome = by_month[month].get(name)
      if outcome is None:
        row.append('-')
      elif outcome.status == 'mismatch':
        row.append(f"{len(outcome.mismatches)} mismatched")
      else:
        row.append(outcome.status)
    rows.append(row)
  _printTable(['month'] + list(source_names), rows)

  mismatched = [outcome for outcome in outcomes if outcome.status == 'mismatch']
  if mismatched:
    print("\nMismatches\n")
    rows = []
    for outcome in mismatched:
      for mismatch in outcome.mismatches:
        rows.append([outcome.month.strftime("%Y-%m"), outcome.source,
                     mismatch.country, mismatch.category, mismatch.field,
                     mismatch.stored, mismatch.computed])
    _printTable(['month', 'source', 'country', 'category', 'field', 'stored', 'computed'],
                rows)

  print()
  failed = [outcome for outcome in outcomes if outcome.failed]
  print(f"{len(outcomes) - len(failed)} of {len(outcomes)} checks matched the stored data")
  for name in source_names:
    bad = [outcome for outcome in failed if outcome.source == name]
    if bad:
      print(f"  {name}: {len(bad)} failed")

  return not failed


@click.command()
@click.option('--cache_dir', type=click.Path(exists=True), required=True,
              help='Directory to store downloaded files. The same cache the '
                   'downloader uses, laid out the same way.')
@click.option('--data_dir', type=click.Path(exists=True), required=True,
              help='Directory holding the stored CSVs to check against.')
@click.option('--start_date', type=_SupportedDateInputs,
              help=f'First month to check. Without it only the last '
                   f'{_DEFAULT_MONTHS} stored months are checked.')
@click.option('--end_date', type=_SupportedDateInputs,
              help='Last month to check. Defaults to the latest stored.')
@click.option('--source', 'source_names', type=click.Choice(sorted(SOURCES)), multiple=True,
              help='Source to check; repeatable. Defaults to every source.')
@click.option('--ignore-cached', is_flag=True, default=False,
              help='Download every bulletin again, ignoring the cache.')
@click.option('--fallback', is_flag=True, default=False,
              help='On a 403 (Cloudflare challenge), retry via a real browser. '
                   'Requires patchright + a browser (see update_data.sh).')
def _main(cache_dir, data_dir, start_date=None, end_date=None, source_names=(),
          ignore_cached=False, fallback=False):
  cache_dir = pathlib.Path(cache_dir).absolute()
  data_dir = pathlib.Path(data_dir).absolute()
  source_names = list(source_names) or sorted(SOURCES)

  months = _storedMonths(data_dir)
  if start_date is not None:
    months = [month for month in months if month >= start_date.date().replace(day=1)]
  if end_date is not None:
    months = [month for month in months if month <= end_date.date().replace(day=1)]
  if start_date is None:
    months = months[-_DEFAULT_MONTHS:]

  if not months:
    raise click.UsageError(f"No stored CSVs to check in {data_dir}")

  fetchers = [RequestsFetcher()]
  fetchers += [ImpersonatingFetcher(name) for name in IMPERSONATIONS]
  if fallback:
    fetchers.append(BrowserFetcher())
  # Nothing is ignored here: a source that cannot be downloaded is a failure,
  # which is the whole point of checking.
  fetcher = ChainFetcher(fetchers)

  print(f"Checking {len(months)} month{'' if len(months) == 1 else 's'} "
        f"against {', '.join(source_names)}")

  outcomes = []
  for name in source_names:
    for target in months:
      outcomes.append(_check(name, target, cache_dir, data_dir, fetcher, ignore_cached))

  if not _report(outcomes, source_names):
    raise SystemExit(1)


if __name__ == '__main__':
  _main()
