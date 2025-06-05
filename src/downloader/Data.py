from __future__ import annotations

import dataclasses
import datetime
import enum
import pathlib
import re

import requests

import bs4

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

class Data:
  def __init__(self, target: datetime.date, path: pathlib.Path):
    self.year = target.year
    self.month = target.month
    self.path = path

  _MONTH_TO_STR = {
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
  def _getMonthStr(self):
    return self._MONTH_TO_STR[self.month]

  def _getWebPage(self):

    url_suffix = "visa-bulletin-for-"
    if ((self.year == 2012) and (self.month == 10)) \
        or ((self.year == 2009) and (self.month == 3)) \
        or ((self.year == 2009) and (self.month in [9, 10, 11])) \
        :
      url_suffix = "visa-bulletin-"

    fiscal_year = self.year + 1 if self.month >= 10 else self.year
    return (
      f"https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin/"
      f"{fiscal_year}"
      f"/{url_suffix}"
      f"{self._getMonthStr()}"
      f"-{self.year}.html"
    )

  def download(self):
    web_page = self._getWebPage()

    if not self.path.exists():
      print(f"Downloading {web_page}")
      resp = requests.get(web_page)
      if resp.status_code != 200:
        raise Exception(f"Failed to download {web_page}, got status code {resp.status_code}")

      page_content = resp.content
      with open(self.path, "wb") as f:
        f.write(page_content)
      return True
    else:
      print(f"Skipping {web_page}")

    return False

  def __str__(self):
    return f"Data({self.year}/{self.month}, {self.path}"

  def extract(self):
    extractor = bs4.BeautifulSoup(open(self.path, encoding="utf8"), "html.parser")

    all_data = []
    for table in extractor.find_all('table'):
      try :
        all_data.extend(self._ExtractTableData(table))
      except Exception as e :
        print(f"Failed to extract data from table:\n{table}")
        raise e

    for data in all_data:
      _ValidateData(data)

    return all_data

  def _ExtractTableData(self, table):
    # Find the type of the table
    ret = []
    container = table.find_parent('div', **{'class': 'section'})
    section_header = container.find_previous_sibling('div', **{'class': 'section'})

    final_action_date = False
    if section_header is not None:
      section_header_text = section_header.get_text().lower()
      if "final action dates" in section_header_text:
        final_action_date = True

    if _IsSkippableTable(table):
      return []

    all_rows = table.find_all('tr')
    data_start_row = 1

    if (self.year < 2003) or ((self.year == 2003) and (self.month <= 9)) \
        or (self.year == 2005 and self.month == 11) or \
        (self.year == 2007 and self.month == 2 and all_rows[0].find_all('td')[0].get_text().strip() == ''):
      # 2007 has one odd table with extra space.
      if len(all_rows) < 2:
        # More weird tables
        return []

      first_row = all_rows[0].find_all(['th', 'td'])
      second_row = all_rows[1].find_all(['th', 'td'])
      headers = [second_row[0]] + first_row[1:]
      data_start_row = 2

    else :
      if (self.year == 2004 and self.month in [2, 3, 4]) :
        # Weird extra row in table
        all_rows = all_rows[1:]
      headers = all_rows[0].find_all(['th', 'td'])

    visa_type_header = headers[0].get_text()
    all_countries = [CountryCategory.get(x.get_text()) for x in headers[1:]]

    for row in all_rows[data_start_row:]:
      if row.get_text().lower().strip() == '':
        # Weird empty row
        continue

      all_entries = row.find_all(['td', 'th'])
      visa_type = VisaCategory.get(all_entries[0].get_text(), visa_type_header)

      for idx, entry in enumerate(all_entries[1:]):
        country = all_countries[idx]
        date_str = entry.get_text().strip()
        date_val = self._ConvertPageDate(date_str)
        ret.append(DataEntry(year = self.year, month=self.month, country=country,
                             visa_type=visa_type, is_final_action_date=final_action_date, date=date_val))

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


def _IsSkippableTable(table) -> bool:
  all_rows = table.find_all('tr')

  if not all_rows :
    return True

  first_row_text = all_rows[0].get_text().lower()
  for name in [
    'dv chargeability areas',
    'africa',
    'asia',
    'europe',
    'north america',
    'oceania',
    'south america, central america, and the caribbean',
  ] :
    if name in first_row_text :
      return True

  previous_paragraph = table.find_previous_sibling('p')
  if previous_paragraph is None and all_rows[0].get_text().strip() == '':
    # Mystery empty table.
    return True

  if previous_paragraph is not None:
    previous_paragraph = previous_paragraph.get_text().lower().strip()
    for name in [
      'dv-2003',
      'dv-2004',
      'dv-2005',
      'dv-2006',
      'dv-2007',
      'dv-2008',
      'dv-2009',
      'dv-2010',
      'dv-2011',
      'dv-2012',
      'dv-2013',
      'dv-2014',
      'dv-2015',
      'dv-2016',
      'dv-2017',
      'dv-2018',
      'dv-2019',
      'dv-2020',
      'dv-2021',
      'dv-2022',
      'dv-2023',
      'dv-2024',
      'dv-2025',
      'all dv chargeability areas',
      'ina 202',
      'possible cut-off date actions based on demand',
      'worldwide dates:',
      'employment third:',
    ] :
      if name in previous_paragraph:
        return True

    # Other ways to detect DV visa
    for name in [
      'africa',
      'asia',
      'europe',
      'oceania',
      'south america, central america, and the caribbean',
      'north america \nbahamas, the 12',
    ] :
      if name == previous_paragraph:
        return True
  return False
