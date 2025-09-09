# SEC EDGAR MCP Tools

This document provides an overview of the available tools in the SEC EDGAR MCP.

## Tools

This project provides a set of tools to interact with SEC EDGAR data. These tools are designed to simplify common tasks related to company information, financial filings, and insider trading data.

### CompanyTools

Tools for company-related operations.

*   **`get_cik_by_ticker(ticker: str)`**: Get the CIK for a company based on its ticker symbol.
*   **`get_company_info(identifier: str)`**: Get detailed company information.
*   **`search_companies(query: str, limit: int = 10)`**: Search for companies by name.
*   **`get_company_facts(identifier: str)`**: Get company facts and financial data.

### FilingsTools

Tools for filing-related operations.

*   **`get_recent_filings(identifier: Optional[str] = None, form_type: Optional[Union[str, List[str]]] = None, days: int = 30, limit: int = 50)`**: Get recent filings for a company or across all companies.
*   **`get_filing_content(identifier: str, accession_number: str, form_type: Optional[str] = None)`**: Get the content of a specific filing.
*   **`analyze_8k(identifier: str, accession_number: str)`**: Analyze an 8-K filing for specific events.
*   **`get_filing_sections(identifier: str, accession_number: str, form_type: str)`**: Get specific sections from a filing.

### FinancialTools

Tools for financial data and XBRL operations.

*   **`get_financials(identifier: str, statement_type: str = "all")`**: Get financial statements for a company by parsing XBRL data from filings.
*   **`get_segment_data(identifier: str, segment_type: str = "geographic")`**: Get segment revenue breakdown.
*   **`get_key_metrics(identifier: str, metrics: Optional[List[str]] = None)`**: Get key financial metrics.
*   **`compare_periods(identifier: str, metric: str, start_year: int, end_year: int)`**: Compare a financial metric across periods.
*   **`discover_company_metrics(identifier: str, search_term: Optional[str] = None)`**: Discover available metrics for a company.
*   **`get_xbrl_concepts(identifier: str, accession_number: Optional[str] = None, concepts: Optional[List[str]] = None, form_type: str = "10-K")`**: Extract specific XBRL concepts from a filing.
*   **`discover_xbrl_concepts(identifier: str, accession_number: Optional[str] = None, form_type: str = "10-K", namespace_filter: Optional[str] = None)`**: Discover all available XBRL concepts in a filing, including company-specific ones.

### InsiderTools

Tools for insider trading data (Forms 3, 4, 5) - simplified version.

*   **`get_insider_transactions(identifier: str, form_types: Optional[List[str]] = None, days: int = 90, limit: int = 50)`**: Get insider transactions for a company.
*   **`get_insider_summary(identifier: str, days: int = 180)`**: Get summary of insider trading activity.
*   **`get_form4_details(identifier: str, accession_number: str)`**: Get detailed information from a specific Form 4.
*   **`analyze_form4_transactions(identifier: str, days: int = 90, limit: int = 50)`**: Analyze Form 4 filings and extract detailed transaction data.
*   **`analyze_insider_sentiment(identifier: str, months: int = 6)`**: Analyze insider trading sentiment - simplified version.

### SearchTools

Keyword search across multiple SEC filings using edgartools' text search.

• `search_filings_text(keyword: str, identifier: Optional[str] = None, forms: Optional[List[str]] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, page: int = 1, page_size: int = 25, order: str = "asc")`

- Purpose: Search filings for a keyword/phrase, filter by company, form type, and date range, return paginated, chronologically ordered results.
- Notes: Requires edgartools with TextSearch support. If unavailable, the tool returns a clear error message.
- Returns: `{ success, results, page, page_size, total, total_pages, order }` where each result includes `accession_number`, `filing_date`, `form_type`, `company_name`, `cik`, `url`, and a `snippet`.

## Manifest and Dispatcher

- `list_tools()`: Returns a JSON manifest of available MCP tools with names, descriptions, and parameter info. Use this first to inspect capabilities.
- `dispatch_tool(description: str, arguments: dict | None = None, dry_run: bool = False)`: Selects the best tool based on a natural-language `description` and optionally executes it with `arguments` (only matching parameters are passed). If `dry_run` is `true`, it only returns the selected tool and signature without execution.

Example:

```
list_tools()

dispatch_tool(
  description="get latest 10-K financials for NVDA",
  arguments={"identifier": "NVDA", "statement_type": "all"}
)
```

## Docker

- Build image: `docker build -t sec-edgar-mcp .`
- Run server: `docker run --rm -e SEC_EDGAR_USER_AGENT="Your Name (email@example.com)" -p 8000:8000 sec-edgar-mcp`
- Notes: The image installs this package via `pyproject.toml` (`pip install .`), avoiding a `requirements.txt`. Dependencies include `mcp[cli]>=1.7.1`, `edgartools`, and `requests`.
