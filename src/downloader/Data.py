import datetime
import pathlib

import requests

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
