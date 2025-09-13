# SEC EDGAR MCP Tools

This MCP server now exposes a minimal, focused toolset for financial statements and recent financial-results press releases.

## Available Tools

- `get_financial_statements(identifier, statement="all", period_type="quarter", periods=1)`
  - Returns income statement, balance sheet, and/or cash flow for the last N quarters or years.
  - `statement`: "income" | "balance" | "cash" | "all"
  - `period_type`: "quarter" | "year"
  - `periods`: number of periods to include
  - Output includes exact values extracted from XBRL plus filing references (form, date, accession, SEC URL).

- `get_recent_financial_results(identifier, count=1)`
  - Returns recent financial-results press releases detected from 8-K (Item 2.02 + EX-99) and 6-K (keyword heuristic).
  - Each item includes `FilingText`, `FilingURL`(s), `FilingDate`, `AccessionNumber`, and `FormType`.

- `get_all_recent_8k(identifier, count=10)`
  - Lists the most recent 8-K or 6-K filings for a company, regardless of type.
  - Each item includes `accession_number`, `filing_date`, `form_type`, `company_name`, `cik`, and `url`.

Notes:
- Data comes directly from SEC EDGAR filings (no estimates or rounding).
- Provide your `SEC_EDGAR_USER_AGENT` via env or `.env` for best results.

## Docker

- Build image: `docker build -t sec-edgar-mcp .`
- Run server: `docker run --rm -e SEC_EDGAR_USER_AGENT="Your Name (email@example.com)" -p 8000:8000 sec-edgar-mcp`
- Notes: The image installs this package via `pyproject.toml` (`pip install .`), avoiding a `requirements.txt`. Dependencies include `mcp[cli]>=1.7.1`, `edgartools`, and `requests`.
