from __future__ import annotations

import bs4

from .Data import IsSkippableFirstRow, RawTable, Source


class HtmlSource(Source):
  """The bulletin as published at travel.state.gov as an HTML page."""

  CACHE_SUFFIX = ".html"

  def url(self) -> str:
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

  def rawTables(self) -> list[RawTable]:
    extractor = bs4.BeautifulSoup(open(self.path, encoding="utf8"), "html.parser")

    ret = []
    for table in extractor.find_all('table'):
      raw = self._toRawTable(table)
      if raw is not None:
        ret.append(raw)

    return ret

  def _toRawTable(self, table) -> RawTable | None:
    # Find the type of the table
    container = table.find_parent('div', **{'class': 'section'})
    section_header = container.find_previous_sibling('div', **{'class': 'section'})

    final_action_date = False
    if section_header is not None:
      section_header_text = section_header.get_text().lower()
      if "final action dates" in section_header_text:
        final_action_date = True

    if _IsSkippableTable(table):
      return None

    all_rows = table.find_all('tr')
    data_start_row = 1

    if (self.year < 2003) or ((self.year == 2003) and (self.month <= 9)) \
        or (self.year == 2005 and self.month == 11) or \
        (self.year == 2007 and self.month == 2 and all_rows[0].find_all('td')[0].get_text().strip() == ''):
      # 2007 has one odd table with extra space.
      if len(all_rows) < 2:
        # More weird tables
        return None

      first_row = all_rows[0].find_all(['th', 'td'])
      second_row = all_rows[1].find_all(['th', 'td'])
      headers = [second_row[0]] + first_row[1:]
      data_start_row = 2

    else :
      if (self.year == 2004 and self.month in [2, 3, 4]) :
        # Weird extra row in table
        all_rows = all_rows[1:]
      headers = all_rows[0].find_all(['th', 'td'])

    return RawTable(
      headers=[x.get_text() for x in headers],
      rows=[[x.get_text() for x in row.find_all(['td', 'th'])]
            for row in all_rows[data_start_row:]],
      is_final_action_date=final_action_date,
      debug=table,
    )


def _IsSkippableTable(table) -> bool:
  all_rows = table.find_all('tr')

  if not all_rows :
    return True

  if IsSkippableFirstRow(all_rows[0].get_text()) :
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
      'north america \nbahamas, the 12',
    ] :
      if name == previous_paragraph:
        return True
  return False
