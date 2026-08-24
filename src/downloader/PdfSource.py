from __future__ import annotations

import dataclasses
import re

import pdfplumber

from .Data import ChartKind, CountryCategory, IsChartName, RawTable, Source

# A cut-off date cell: 22JAN20, C (current) or U (unavailable).
_VALUE_RE = re.compile(r'^(\d{1,2}[A-Za-z]{3}\d{2}|[CU])$')

# Words within this many points of each other vertically are one line.
_LINE_TOLERANCE = 3

# A line needs this many date cells before it counts as a row of a chart. The
# narrowest chart has five country columns, so this tolerates a couple of cells
# whose text came out of the PDF split or malformed.
_MIN_VALUES = 3

# How many lines above a chart to look through for its column headings. Each
# column's heading wraps independently, so one row of them spans a good many
# lines -- and they are not always set apart from the paragraph above them.
_MAX_HEADER_LINES = 14

# How much closer the line below has to be than the line above before a line is
# taken to belong with it rather than with the one above.
_TIE_TOLERANCE = 1.05

# The PDFs head the three set aside rows with a single plural heading. The
# bulletin calls each of them "5th Set Aside:" wherever it names one in full,
# which is how the HTML pages give it and what the categories are keyed on.
_PLURAL_GROUP_RE = re.compile(r'\bSet Asides:', re.IGNORECASE)

_FINAL_ACTION_HEADING = 'final action date'
_FILING_HEADING = 'dates for filing'


class PdfSource(Source):
  """The bulletin as published at travel.state.gov as a PDF.

  Unlike the HTML pages, the PDF is served off an asset path that is not behind
  the Cloudflare "Verify you are human" challenge, so it can be retrieved
  without driving a browser.

  The charts are rebuilt from where the words sit on the page rather than from
  the table's ruling lines: the bulletins draw the filing charts with ruled
  cells but the final action charts with none at all, and reading the geometry
  handles both. It also sidesteps the diversity visa tables for free, since
  those hold quotas and region names rather than cut-off dates.
  """

  CACHE_SUFFIX = ".pdf"

  def url(self) -> str:
    return (
      f"https://travel.state.gov/content/dam/visas/Bulletins/"
      f"visabulletin_{self._getMonthStr().capitalize()}{self.year}.pdf"
    )

  def rawTables(self) -> list[RawTable]:
    tables = []
    # All of this carries across pages: a chart routinely breaks over a page
    # boundary, and its heading sits back on the page it started on.
    final_action_date = False
    chart = None
    group = ""
    preceding = []

    with pdfplumber.open(self.path) as pdf:
      for page in pdf.pages:
        for block in _blocks(page):
          heading = _headingSection(block.text)
          if heading is not None:
            final_action_date = heading
            chart, group = None, ""
            # The column headings are not always set apart from the paragraph
            # that announces the section, so keep its lines to read them from.
            preceding = block.lines[-_MAX_HEADER_LINES:]
            continue

          values = [word for word in block.words if _VALUE_RE.match(word.text)]

          if len(values) >= _MIN_VALUES:
            columns = chart.columns if chart is not None else _Columns(values)
            first = next(index for index, line in enumerate(block.lines)
                         if _isDataLine(line))
            lead, rest = block.lines[:first], block.lines[first:]

            if chart is None:
              opened = _startChart(columns, preceding, lead, final_action_date, tables)
              chart, lead = opened.chart, opened.label
              if opened.started:
                tables.append(chart)
            else:
              lead = [line for line in lead if _inGutter(columns, line)]

            chart.rows.append(_readRow(chart, lead + rest, group))
            preceding = []
            continue

          if chart is not None and _isLabelOnly(chart, block):
            if block.text.rstrip().endswith(':'):
              # Applies to every row below it, so it is remembered, not spent.
              # A heading over the label column naming the rows below it: the
              # "5th Set Asides:" that the rows beneath only qualify.
              group = _PLURAL_GROUP_RE.sub('Set Aside:', block.text)
            elif chart.rows:
              # The tail of the row above, set apart from it.
              chart.rows[-1][0] = _joinLabel([chart.rows[-1][0], block.text])
            continue

          chart, group = None, ""
          preceding.extend(block.lines)
          del preceding[:-_MAX_HEADER_LINES]

    _checkComplete(tables)
    return tables


def _checkComplete(tables):
  """Refuse a bulletin whose charts did not all come out.

  A layout this does not understand does not announce itself: a chart that goes
  unrecognised leaves its dates simply missing, and a section heading that goes
  unread files a chart under the wrong one. Either shows up as the charts no
  longer pairing off -- one of the two per section, per chart -- so that is what
  is checked, rather than letting a bulletin through half-read.
  """
  found = {}
  for table in tables:
    key = (ChartKind(table.headers[0]), table.is_final_action_date)
    if key in found:
      raise Exception(f"Read two {_describe(key)} charts out of one bulletin")
    found[key] = table

  sections = {section for _, section in found}
  for kind, _ in list(found):
    for section in sections:
      if (kind, section) not in found:
        raise Exception(f"No {_describe((kind, section))} chart in this bulletin; "
                        f"its layout is not one this can read")


def _describe(key) -> str:
  kind, final_action = key
  return f"{kind} {'final action' if final_action else 'filing'}"


class _Word:
  """A word and where it sits, so columns can be read off the page."""

  __slots__ = ('text', 'x0', 'x1', 'top')

  def __init__(self, word):
    self.text = word['text'].strip()
    self.x0 = word['x0']
    self.x1 = word['x1']
    self.top = word['top']

  @property
  def center(self):
    return (self.x0 + self.x1) / 2


class _Line:
  """One line of a page, left to right."""

  __slots__ = ('words', 'text', 'top')

  def __init__(self, words):
    self.words = sorted(words, key=lambda word: word.x0)
    self.text = " ".join(word.text for word in self.words)
    self.top = min(word.top for word in self.words)


class _Block:
  """Consecutive lines set solid: one chart row, one heading, one paragraph."""

  __slots__ = ('lines', 'words', 'text')

  def __init__(self, lines):
    self.lines = lines
    self.words = [word for line in lines for word in line.words]
    self.text = " ".join(line.text for line in lines)


def _textLines(page) -> list[_Line]:
  """Group a page's words into lines, top to bottom."""
  lines = []
  current = []
  current_top = None

  for word in sorted(page.extract_words(), key=lambda w: (w['top'], w['x0'])):
    if current_top is not None and abs(word['top'] - current_top) > _LINE_TOLERANCE:
      lines.append(_Line(current))
      current = []
      current_top = None

    if current_top is None:
      current_top = word['top']
    current.append(_Word(word))

  if current:
    lines.append(_Line(current))

  return lines


def _blocks(page) -> list[_Block]:
  """Split a page into blocks: one per chart row, plus everything in between.

  The bulletins do not rule the final action charts, so nothing marks where one
  row ends and the next begins except where the words sit. A row's label wraps
  over several lines and can start above its dates as well as continue below
  them, so each line is given to whichever row's dates it sits nearest -- and
  to none at all if it sits too far from any of them to be part of one.
  """
  lines = _textLines(page)
  if not lines:
    return []

  data = [index for index, line in enumerate(lines) if _isDataLine(line)]
  if not data:
    return [_Block(lines)]

  owners = _owners(lines, data, _ruledRows(page))

  blocks = []
  current = [lines[0]]
  held_by = owners.get(0)

  for index in range(1, len(lines)):
    if owners.get(index) != held_by:
      blocks.append(_Block(current))
      current = []
      held_by = owners.get(index)
    current.append(lines[index])
  blocks.append(_Block(current))

  return blocks


@dataclasses.dataclass
class _Band:
  """The span of the page one ruled cell covers, top to bottom."""
  top: float
  bottom: float

  def holds(self, line) -> bool:
    return self.top <= line.top < self.bottom


def _ruledRows(page) -> list[_Band]:
  """The bands a page's ruled cells divide it into, top to bottom."""
  return [_Band(top=row.bbox[1], bottom=row.bbox[3])
          for table in page.find_tables() for row in table.rows]


def _owners(lines, data, ruled) -> dict:
  """Work out which row's dates, if any, each line belongs to.

  Where the chart is ruled, the rules say it: everything inside a cell is one
  row, however the lines inside it happen to be spaced. The bulletins only rule
  some of their charts though, and where they do not, every line is set closer
  to whichever of its neighbours it goes with -- so each is followed to its
  nearer neighbour, and that one to its own, until the chain arrives at a row's
  dates. Lines that only lead to each other belong to no row: body text, or a
  heading standing over the rows beneath it.
  """
  rows = set(data)
  owners = {index: index for index in data}

  # Rows whose dates fall in a ruled cell take their lines from that cell and
  # from nowhere else, which keeps the letterhead at the top of a page out of
  # the first row beneath it.
  ruled_rows = {}
  for band in ruled:
    inside = [index for index, line in enumerate(lines) if band.holds(line)]
    within = [index for index in inside if index in rows]
    if len(within) != 1:
      continue
    ruled_rows[within[0]] = set(inside)
    for index in inside:
      owners.setdefault(index, within[0])

  nearer = {}

  for index in range(len(lines)):
    if index in rows:
      continue

    above = lines[index].top - lines[index - 1].top if index > 0 else None
    below = lines[index + 1].top - lines[index].top if index < len(lines) - 1 else None

    if above is None and below is None:
      continue
    # Ties, and near enough to ties, go upward: a label that wraps follows the
    # dates it belongs to far more often than it precedes them, and the two
    # gaps around a wrapped line differ by only a rounding.
    if below is None or (above is not None and above <= below * _TIE_TOLERANCE):
      nearer[index] = index - 1
    else:
      nearer[index] = index + 1

  for index in range(len(lines)):
    if index in owners:
      continue

    seen = set()
    step = index
    while step in nearer and step not in seen:
      seen.add(step)
      step = nearer[step]
      if step in rows:
        if step not in ruled_rows:
          owners[index] = step
        break

  return owners


def _isDataLine(line) -> bool:
  return sum(bool(_VALUE_RE.match(word.text)) for word in line.words) >= _MIN_VALUES


def _firstValue(line) -> int:
  """Where the dates start on a line, everything before them being label."""
  return next(position for position, word in enumerate(line.words)
              if _VALUE_RE.match(word.text))


def _headingSection(text: str):
  """True/False if this block announces a section, None if it announces nothing.

  Both phrases can turn up together (a filing heading often refers back to
  final action dates), so whichever is mentioned last is the one that applies.
  """
  text = text.lower()
  final_action = text.rfind(_FINAL_ACTION_HEADING)
  filing = text.rfind(_FILING_HEADING)

  if final_action < 0 and filing < 0:
    return None
  return final_action > filing


class _Columns:
  """Where a chart's columns sit, as boundaries across the page.

  Headings are centred over their column and run wider than the dates beneath,
  so a word belongs to whichever column centre it is nearest rather than having
  to land within the dates' own extent. Everything left of the first column is
  the row label.
  """

  def __init__(self, values):
    self.centers = [word.center for word in values]

    spacing = [b - a for a, b in zip(self.centers, self.centers[1:])]
    lead = min(spacing) if spacing else 0
    self.left_edge = self.centers[0] - lead / 2
    self.boundaries = [(a + b) / 2 for a, b in zip(self.centers, self.centers[1:])]

  def __len__(self):
    return len(self.centers)

  def of(self, word) -> int | None:
    """Which column a word belongs to, or None when it is a row label."""
    if word.center < self.left_edge:
      return None

    for index, boundary in enumerate(self.boundaries):
      if word.center < boundary:
        return index
    return len(self.centers) - 1


class _Chart(RawTable):
  """A RawTable that still knows where its columns sit on the page."""

  def __init__(self, columns, headers, rows, is_final_action_date, debug):
    super().__init__(headers=headers, rows=rows,
                     is_final_action_date=is_final_action_date, debug=debug)
    self.columns = columns


def _inGutter(columns, line) -> bool:
  """Whether a line keeps left of the columns, where the row labels run."""
  return all(columns.of(word) is None for word in line.words)


@dataclasses.dataclass
class _Opened:
  """The chart a row belongs to, and what of its lines were not headings.

  started is False when the row turned out to belong to a chart already under
  way, which the caller must not record twice.
  """
  chart: '_Chart'
  started: bool
  label: list


def _startChart(columns, preceding, lead, final_action_date, tables) -> _Opened:
  """Find the chart these dates belong to.

  The lines above the first row run from body text through the column headings
  and on into the row's own label, in no fixed order -- some bulletins put the
  name of the label column above the country names, some below. So the headings
  are taken to be whatever run of those lines reads as a heading, and whatever
  is left under them opens the first row's label.

  """
  headers = None
  label = []

  for kept in range(len(lead), -1, -1):
    headers = _readHeaders(columns, preceding, lead[:kept])
    if headers is not None:
      label = [line for line in lead[kept:] if _inGutter(columns, line)]
      break

  if headers is None:
    # Nothing above these dates names their columns: the tail of a chart broken
    # over a page break, so carry on with the one it was split from.
    if tables and len(tables[-1].headers) == len(columns) + 1:
      return _Opened(chart=tables[-1], started=False,
                     label=[line for line in lead if _inGutter(columns, line)])
    headers = []

  chart = _Chart(columns=columns, headers=headers, rows=[],
                 is_final_action_date=final_action_date,
                 debug="\n".join(line.text for line in preceding))
  return _Opened(chart=chart, started=True, label=label)


def _readHeaders(columns, preceding, headings) -> list[str] | None:
  """Read the column headings sitting above a chart.

  The lines above a chart run from body text into the headings themselves, and
  nothing about a line says which it is -- so the headings are taken to be the
  fewest lines above the chart that name a country in every column and name the
  chart itself. Returns None when no run of them does, which means the chart
  began on an earlier page.
  """
  for depth in range(0, len(preceding) + 1):
    lines = preceding[len(preceding) - depth:] if depth else []
    cells = _readCells(columns, lines + headings)

    if any(not cell for cell in cells):
      continue
    if IsChartName(cells[0]) and all(_isCountry(cell) for cell in cells[1:]):
      return cells

  return None


def _readCells(columns, lines) -> list[list[str]]:
  """Lay a run of lines out into a label and one cell per column."""
  cells = [[] for _ in range(len(columns) + 1)]

  for line in lines:
    for word in line.words:
      index = columns.of(word)
      cells[0 if index is None else index + 1].append(word.text)

  return [" ".join(cell) for cell in cells]


def _isCountry(heading: str) -> bool:
  try:
    CountryCategory.get(heading)
  except Exception:
    return False
  return True


def _readRow(chart, lines, group: str) -> list[str]:
  """Split one row's lines into its label and one cell per column."""
  cells = [[] for _ in range(len(chart.columns) + 1)]

  for line in lines:
    # Only the line carrying the dates fills the columns, and on that line only
    # from its first date rightwards. A label runs on under the columns --
    # "(Rural: NR, RR - 20%)" reaches well into them -- and is label throughout,
    # while a date the PDF split in two ("22" "JAN14") still has to land in one.
    start = _firstValue(line) if _isDataLine(line) else None

    for position, word in enumerate(line.words):
      index = chart.columns.of(word) if start is not None and position >= start else None
      cells[0 if index is None else index + 1].append(word.text)

  label = _joinLabel(cells[0])
  if group and not label.startswith(group):
    # A heading over several rows, which the rows that repeat it do not need.
    label = f"{group} {label}".strip()

  # A date can come out of the PDF split into pieces ("22" "JAN14"), so the
  # pieces of a cell are joined up rather than spaced apart.
  return [label] + ["".join(cell) for cell in cells[1:]]


def _joinLabel(words: list[str]) -> str:
  """Join a row label, closing up words the PDF broke across lines.

  "Infra-" above "structure" is one word; "Employment-" above "Based" is not.
  A lower case continuation marks the difference.
  """
  label = ""
  for word in words:
    if label.endswith('-') and word[:1].islower():
      label = label[:-1] + word
    elif label:
      label += f" {word}"
    else:
      label = word
  return label


def _isLabelOnly(chart, block) -> bool:
  """Whether every word in this block sits left of the first column."""
  return all(chart.columns.of(word) is None for word in block.words)
