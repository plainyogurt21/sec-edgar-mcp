# SEC EDGAR MCP Tools

This document provides an overview of the available tools in the SEC EDGAR MCP.

## Filings Tools

These tools are used for filing-related operations.

### `get_recent_filings(identifier: str = None, form_type: str = None, days: int = 30, limit: int = 50)`

Get recent SEC filings for a company or across all companies.

**Inputs:**

- `identifier` (str, optional): Company ticker/CIK (if not provided, returns all recent filings).
- `form_type` (str, optional): Specific form type to filter (e.g., "10-K", "10-Q", "8-K").
- `days` (int, optional): Number of days to look back (default: 30).
- `limit` (int, optional): Maximum number of filings to return (default: 50).

**Output:**

A dictionary containing a list of recent filings.

**Example:**

```json
{
  "success": true,
  "filings": [
    {
      "accession_number": "0000320193-24-000080",
      "filing_date": "2024-08-01T00:00:00",
      "form_type": "8-K",
      "company_name": "Apple Inc.",
      "cik": 320193,
      "file_number": "001-36743",
      "acceptance_datetime": "2024-08-01T16:05:24",
      "period_of_report": "2024-08-01T00:00:00"
    }
  ],
  "count": 1
}
```

### `get_filing_content(identifier: str, accession_number: str)`

Get the content of a specific SEC filing.

**Inputs:**

- `identifier` (str): Company ticker symbol or CIK number.
- `accession_number` (str): The accession number of the filing.

**Output:**

A dictionary containing filing content and metadata.

**Example:**

```json
{
  "success": true,
  "accession_number": "0000320193-24-000080",
  "form_type": "8-K",
  "filing_date": "2024-08-01T00:00:00",
  "content": "...",
  "content_truncated": true,
  "filing_data": {},
  "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000080/a8-kex991q3202406292024.htm"
}
```

### `analyze_8k(identifier: str, accession_number: str)`

Analyze an 8-K filing for specific events and items.

**Inputs:**

- `identifier` (str): Company ticker symbol or CIK number.
- `accession_number` (str): The accession number of the 8-K filing.

**Output:**

A dictionary containing analysis of 8-K items and events, including the content of press releases and items.

**Example:**

```json
{
  "success": true,
  "analysis": {
    "date_of_report": "2024-08-01T00:00:00",
    "items": [
      "Item 2.02",
      "Item 9.01"
    ],
    "events": {},
    "has_press_release": true,
    "press_releases": [
      {
        "description": "EX-99.1",
        "content": "..."
      }
    ],
    "item_details": {
      "Item 2.02": "...",
      "Item 9.01": "..."
    }
  }
}
```

### `get_filing_sections(identifier: str, accession_number: str, form_type: str)`

Get specific sections from a filing (e.g., business description, risk factors, MD&A).

**Inputs:**

- `identifier` (str): Company ticker symbol or CIK number.
- `accession_number` (str): The accession number of the filing.
- `form_type` (str): The type of form (e.g., "10-K", "10-Q").

**Output:**

A dictionary containing available sections from the filing.

**Example:**

```json
{
  "success": true,
  "form_type": "8-K",
  "sections": {},
  "available_sections": []
}
```