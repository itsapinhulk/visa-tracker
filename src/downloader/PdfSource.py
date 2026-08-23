from __future__ import annotations

from .Data import RawTable, Source


class PdfSource(Source):
  """The bulletin as published at travel.state.gov as a PDF.

  Unlike the HTML pages, the PDF is served off an asset path that is not behind
  the Cloudflare "Verify you are human" challenge, so it can be retrieved
  without driving a browser.

  Downloading is all this does for now -- nothing parses the PDF yet.
  """

  CACHE_SUFFIX = ".pdf"

  def url(self) -> str:
    return (
      f"https://travel.state.gov/content/dam/visas/Bulletins/"
      f"visabulletin_{self._getMonthStr().capitalize()}{self.year}.pdf"
    )

  def rawTables(self) -> list[RawTable]:
    raise NotImplementedError(f"Reading tables out of {self.path} is not implemented yet")
