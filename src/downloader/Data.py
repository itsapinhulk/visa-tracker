from __future__ import annotations

import dataclasses
import datetime
import enum
import pathlib
import re

class CountryCategory(enum.Enum):
  INDIA = 'India'
  CHINA = 'China'
  MEXICO = 'Mexico'
  PHILIPPINES = 'Philippines'
  EL_SALVADOR_GUATEMALA_HONDURAS = 'El Salvador/Guatemala/Honduras'
  VIETNAM = 'Vietnam'
  DOMINICAN_REPUBLIC = 'Dominican Republic'
  REST_OF_WORLD = 'Rest-of-World'

  @staticmethod
  def get(inpStr : str) -> CountryCategory:
    inpStr = inpStr.strip()
    inpStr = inpStr.lower()
    inpStr = re.sub(r'[ \n\xc2\xa0]+', ' ', inpStr)

    # Make sure we get exact match to not miscategorize anything
    if inpStr in ['india', 'in'] :
      return CountryCategory.INDIA
    elif inpStr in ['china', 'china-mainland born', 'china- mainland born', \
                    'china - mainland born', 'ch'] :
      return CountryCategory.CHINA
    elif inpStr in ['mexico', 'me'] :
      return CountryCategory.MEXICO
    elif inpStr in ['philippines', 'philip-pines', 'phillipines', 'philipp-ines', 'ph'] :
      return CountryCategory.PHILIPPINES
    elif inpStr in ['el salvador guatemala honduras'] :
      return CountryCategory.EL_SALVADOR_GUATEMALA_HONDURAS
    elif inpStr in ['vietnam'] :
      return CountryCategory.VIETNAM
    if inpStr in ['dominican republic'] :
      return CountryCategory.DOMINICAN_REPUBLIC
    elif inpStr in [
      'all chargeability areas except those listed',
      'all chargeability areas except hose listed',
      'all chargability area except those listed',
      'all charge- ability areas except those listed',
      'all charge ability areas except those listed',
    ] :
      return CountryCategory.REST_OF_WORLD

    raise Exception(f"Unknown country category {inpStr.encode()}")

class VisaCategory(enum.Enum):
  # Employment based visas
  EB1 = 'EB1'
  EB2 = 'EB2'
  EB3 = 'EB3'
  EB_OTHER = 'EB-Other'
  EB_SCHEDULE_A = 'EB-Schedule-A'
  EB4 = 'EB4'
  EB5 = 'EB5'
  EB_RELIGIOUS = 'EB-Religious'
  EB_IRAQI_AFGHANI_TRANSLATORS = 'EB-Iraqi-Afghani-Translators'
  EB5_UNRESERVED = 'EB5-Unreserved'
  EB5_RURAL = 'EB5-Rural'
  EB5_HIGH_UNEMPLOYMENT = 'EB5-High-Unemployment'
  EB5_INFRASTRUCTURE = 'EB5-Infrastructure'
  EB5_TARGETED_EMPLOYMENT = 'EB5-Targeted-Employment'
  EB5_NON_REGIONAL_CENTER = 'EB5-Non-Regional-Center'
  EB5_REGIONAL_CENTER = 'EB5-Regional-Center'
  EB5_PILOT_PROGRAMS = 'EB5-Pilot-Programs'

  # Family based visas
  F1 = 'F1'
  F2A = 'F2A'
  F2B = 'F2B'
  F3 = 'F3'
  F4 = 'F4'

  @staticmethod
  def get(inpStr, visa_type):
    inpStr = _SanitizeTextData(inpStr)

    visa_type = _SanitizeTextData(visa_type)

    if visa_type in ['family- sponsored', 'family']:
      if inpStr in ['f1', '1st']:
        return VisaCategory.F1
      elif inpStr in ['f2a', '2a*', '2a', 'f2a*']:
        return VisaCategory.F2A
      elif inpStr in ['f2b', '2b']:
        return VisaCategory.F2B
      elif inpStr in ['f3', '3rd']:
        return VisaCategory.F3
      elif inpStr in ['f4', '4th', '4rd']:
        return VisaCategory.F4

    elif visa_type in ['employment- based', 'employment-based', 'employment - based',
                       'employment -based', 'employment based']:
      if inpStr in ['1st']:
        return VisaCategory.EB1
      elif inpStr in ['2nd']:
        return VisaCategory.EB2
      elif inpStr in ['3rd']:
        return VisaCategory.EB3
      elif inpStr in ['schedule a workers']:
        return VisaCategory.EB_SCHEDULE_A
      elif inpStr in ['other workers', 'other worker', 'other workers*']:
        return VisaCategory.EB_OTHER
      elif inpStr in ['4th']:
        return VisaCategory.EB4
      elif inpStr in ['5th']:
        return VisaCategory.EB5
      elif inpStr in ['certain religious workers', 'certain religiuos workers']:
        return VisaCategory.EB_RELIGIOUS
      elif inpStr in ['iraqi & afghani translators'] :
        return VisaCategory.EB_IRAQI_AFGHANI_TRANSLATORS
      elif inpStr.startswith('5th unreserved'):
        return VisaCategory.EB5_UNRESERVED
      elif inpStr.startswith('5th set aside: rural') \
          or inpStr.startswith('5th set aside: (rural'):
        return VisaCategory.EB5_RURAL
      elif inpStr.startswith('5th set aside: high unemployment') \
          or inpStr.startswith('5th set aside: (high unemployment'):
        return VisaCategory.EB5_HIGH_UNEMPLOYMENT
      elif inpStr.startswith('5th set aside: infrastructure') \
          or inpStr.startswith('5th set aside: (infrastructure'):
        return VisaCategory.EB5_INFRASTRUCTURE
      elif inpStr.startswith('5th targeted employmentareas') or \
          inpStr.startswith('targeted employment areas') or \
          inpStr.startswith('targeted employ- ment areas') or \
          inpStr.startswith('targeted employ-ment areas') or \
          inpStr.startswith('5th targeted employment areas'):
        return VisaCategory.EB5_TARGETED_EMPLOYMENT
      elif inpStr.startswith('5th non-regional center'):
        return VisaCategory.EB5_NON_REGIONAL_CENTER
      elif inpStr.startswith('5th regional center'):
        return VisaCategory.EB5_REGIONAL_CENTER
      elif inpStr.startswith('5th pilot progams') or \
          inpStr.startswith('5th pilot programs'):
        return VisaCategory.EB5_PILOT_PROGRAMS

    raise Exception(f"Unknown visa category {inpStr.encode()} with header {visa_type.encode()}")

@dataclasses.dataclass
class DataEntry:
  year: int
  month: int
  country: CountryCategory
  visa_type: VisaCategory
  is_final_action_date: bool
  date: datetime.date


@dataclasses.dataclass
class RawTable:
  """One cut-off date table, flattened out of whatever source produced it.

  Sources (HTML, PDF) differ wildly in how a table has to be located and how
  its header is laid out, so each source resolves that itself and hands back
  plain text cells. Everything downstream -- category lookup, date parsing,
  DataEntry construction -- is shared (see Source.tableToEntries).

  headers: first cell is the visa type header ("Employment- based"), the rest
           are the country columns.
  rows:    data rows, each starting with the visa category label ("2nd").
  debug:   source-specific context (raw table markup, page number) printed when
           a row fails to parse.
  """
  headers: list[str]
  rows: list[list[str]]
  is_final_action_date: bool
  debug: object = None


MONTH_TO_STR = {
  1: "january",
  2: "february",
  3: "march",
  4: "april",
  5: "may",
  6: "june",
  7: "july",
  8: "august",
  9: "september",
  10: "october",
  11: "november",
  12: "december",
}


class Source:
  """Base class for a bulletin source: locate a month, yield its tables.

  Subclasses implement url() and rawTables(); download(), extract() and the
  parsing helpers below are shared. How the URL is actually retrieved is not a
  source's concern -- that is a Fetcher (see Http.py).
  """

  # File extension used for this source's cache entries.
  CACHE_SUFFIX = None

  def __init__(self, target: datetime.date, path: pathlib.Path):
    self.year = target.year
    self.month = target.month
    self.path = path

  def _getMonthStr(self):
    return MONTH_TO_STR[self.month]

  def url(self) -> str:
    raise NotImplementedError

  def rawTables(self) -> list[RawTable]:
    """Parse the cached file at self.path into RawTables."""
    raise NotImplementedError

  def download(self, fetcher):
    """Fetch this month's document into the cache, overwriting what is there.

    Returns the HTTP status: 200 when the document was written, 404 when the
    site does not have it, None when the fetcher gave up. Whether it was worth
    downloading at all, and what a failure means -- give up, or reach for
    another source -- is the caller's call.
    """
    status, content = fetcher.fetch(self.url())
    if status == 200:
      with open(self.path, "wb") as f:
        f.write(content)

    return status

  def __str__(self):
    return f"{type(self).__name__}({self.year}/{self.month}, {self.path}"

  def extract(self):
    all_data = []
    for table in self.rawTables():
      try :
        all_data.extend(self.tableToEntries(table))
      except Exception as e :
        print(f"Failed to extract data from table:\n{table.debug}")
        raise e

    for data in all_data:
      _ValidateData(data)

    return all_data

  def tableToEntries(self, table: RawTable) -> list[DataEntry]:
    ret = []

    visa_type_header = table.headers[0]
    all_countries = [CountryCategory.get(x) for x in table.headers[1:]]

    for row in table.rows:
      if ''.join(row).lower().strip() == '':
        # Weird empty row
        continue

      visa_type = VisaCategory.get(row[0], visa_type_header)

      for idx, entry in enumerate(row[1:]):
        country = all_countries[idx]
        date_val = self._ConvertPageDate(entry.strip())
        ret.append(DataEntry(year = self.year, month=self.month, country=country,
                             visa_type=visa_type, is_final_action_date=table.is_final_action_date,
                             date=date_val))

    return ret

  _MONTH_TO_INT = {
    'JAN': 1,
    'FEB': 2,
    'MAR': 3,
    'APR': 4,
    'MAY': 5,
    'JUN': 6,
    'JUL': 7,
    'AUG': 8,
    'SEP': 9,
    'OCT': 10,
    'NOV': 11,
    'DEC': 12,
  }
  def _ConvertPageDate(self, date_str) -> datetime.date | None:
    date_str = date_str.lower()
    if date_str == 'c' :
      return datetime.date(year=self.year, month=self.month, day=1)
    if date_str == 'u' :
      return None
    if date_str == '' :
      return None

    if date_str == '2oct91':
      date_str = '02oct91'

    if date_str == '8may97' :
      date_str = '08may97'

    day_str = date_str[0:2]
    day = int(day_str)
    month = self._MONTH_TO_INT[date_str[2:5].upper()]
    year = int(date_str[5:7])
    if year >= 80 :
      year += 1900
    else :
      year += 2000

    return datetime.date(year=year, month=month, day=day)


def _ValidateData(allData : list[DataEntry]):
  pass


def _SanitizeTextData(inpStr : str) -> str:
  inpStr = inpStr.strip()
  inpStr = inpStr.lower()
  return re.sub(r'[ \n\xc2\xa0]+', ' ', inpStr)


# Diversity visa tables share the page with the cut-off date tables we want but
# are keyed by region rather than country, so every source has to drop them.
_DV_ROW_NAMES = [
  'dv chargeability areas',
  'africa',
  'asia',
  'europe',
  'north america',
  'oceania',
  'south america, central america, and the caribbean',
]


def IsSkippableFirstRow(first_row_text: str) -> bool:
  first_row_text = first_row_text.lower()
  for name in _DV_ROW_NAMES:
    if name in first_row_text :
      return True
  return False
