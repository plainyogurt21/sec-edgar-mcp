import argparse
import os
import inspect
import re
from typing import Optional, Any, Dict
from mcp.server.fastmcp import FastMCP
from sec_edgar_mcp.tools import FinancialTools, ResultsTools


# Initialize MCP server
mcp = FastMCP("SEC EDGAR MCP", dependencies=["edgartools"]) 

# KISS: disable auto-registration from legacy decorators, we will explicitly register
__register_tool = mcp.tool
def __noop_tool(name: str):
    def _decorator(fn):
        return fn
    return _decorator
mcp.tool = __noop_tool  # type: ignore

# HTTP app is created only if/when HTTP transport is selected
http_app: Optional[object] = None

# Add system-wide instructions for deterministic responses
DETERMINISTIC_INSTRUCTIONS = """
CRITICAL: When responding to SEC filing data requests, you MUST follow these rules:

1. ONLY use data from the SEC filing provided by the tools - NO EXTERNAL KNOWLEDGE
2. ALWAYS include complete filing reference information:
   - Filing date, form type, accession number
   - Direct SEC URL for verification
   - Period/context for each data point
3. NEVER add external knowledge, estimates, interpretations, or calculations
4. NEVER analyze trends, provide context, or make comparisons not in the filing
5. Be completely deterministic - identical queries must give identical responses
6. If data is not in the filing, state "Not available in this filing" - DO NOT guess or estimate
7. ALWAYS specify the exact period/date/context for each piece of data from the XBRL
8. PRESERVE EXACT NUMERIC PRECISION - NO ROUNDING! Use the exact values from the filing
9. Include clickable SEC URL so users can independently verify all data
10. State that all data comes directly from SEC EDGAR filings with no modifications

EXAMPLE RESPONSE FORMAT:
"Based on [Company]'s [Form Type] filing dated [Date] (Accession: [Number]):
- [Data point]: $37,044,000,000 (Period: [Date]) - EXACT VALUE, NO ROUNDING
- [Data point]: $12,714,000,000 (Period: [Date]) - EXACT VALUE, NO ROUNDING

Source: SEC EDGAR Filing [Accession Number], extracted directly from XBRL data with no rounding or estimates.
Verify at: [SEC URL]"

CRITICAL: NEVER round numbers like "$37.0B" - always show exact values like "$37,044,000,000"

YOU ARE A FILING DATA EXTRACTION SERVICE, NOT A FINANCIAL ANALYST OR ADVISOR.
"""

# Initialize minimal tool classes
financial_tools = FinancialTools()
results_tools = ResultsTools()

# Centralized list of MCP tool function names to expose in the manifest.
# This avoids guessing FastMCP internals and keeps things explicit and readable.
TOOL_NAMES = [
    "get_financial_statements",
    "get_recent_financial_results",
    "get_all_recent_8k",
]


def get_financial_statements(identifier: str, statement: str = "all", period_type: str = "quarter", periods: int = 1):
    """
    Get income, balance, and/or cash flow statements for the last N quarters or years.

    Args:
        identifier: Company ticker or CIK
        statement: "income" | "balance" | "cash" | "all"
        period_type: "quarter" or "year"
        periods: number of periods to include (default: 1)

    Returns:
        Statements keyed by filing date with filing references and exact values from XBRL.
    """
    return financial_tools.get_financial_statements(identifier, statement, period_type, periods)


def get_recent_financial_results(identifier: str, count: int = 1):
    """
    Get the most recent financial-results press releases (8-K/6-K).

    Returns FilingText, FilingURL(s), FilingDate, AccessionNumber, and FormType.
    """
    return results_tools.get_recent_financial_results(identifier, count)

def get_all_recent_8k(identifier: str, count: int = 10):
    """
    List the most recent 8-K or 6-K filings for a company, regardless of type.

    Returns accession_number, filing_date, form_type, company_name, cik, and URL.
    """
    return results_tools.get_all_recent_8k(identifier, count)

# Explicitly register only the minimal tools
__register_tool("get_financial_statements")(get_financial_statements)
__register_tool("get_recent_financial_results")(get_recent_financial_results)
__register_tool("get_all_recent_8k")(get_all_recent_8k)

# Restore the original decorator for any future use
mcp.tool = __register_tool  # type: ignore


@mcp.tool("get_company_facts")
def get_company_facts(identifier: str):
    """
    Get company facts and key financial metrics.

    Args:
        identifier: Company ticker symbol or CIK number

    Returns:
        Dictionary containing available financial metrics
    """
    return company_tools.get_company_facts(identifier)


# Filing Tools
@mcp.tool("get_recent_filings")
def get_recent_filings(identifier: str = None, form_type: str = None, days: int = 30, limit: int = 50):
    """
    Get recent SEC filings for a company or across all companies.

    Args:
        identifier: Company ticker/CIK (optional, if not provided returns all recent filings)
        form_type: Specific form type to filter (e.g., "10-K", "10-Q", "8-K")
        days: Number of days to look back (default: 30)
        limit: Maximum number of filings to return (default: 50)

    Returns:
        Dictionary containing list of recent filings
    """
    return filings_tools.get_recent_filings(identifier, form_type, days, limit)


@mcp.tool("get_filing_content")
def get_filing_content(identifier: str, accession_number: str):
    """
    Get the content of a specific SEC filing.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The accession number of the filing

    Returns:
        Dictionary containing filing content and metadata
    """
    return filings_tools.get_filing_content(identifier, accession_number)


@mcp.tool("analyze_8k")
def analyze_8k(identifier: str, accession_number: str):
    """
    Analyze an 8-K filing for specific events and items.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The accession number of the 8-K filing

    Returns:
        Dictionary containing analysis of 8-K items and events
    """
    return filings_tools.analyze_8k(identifier, accession_number)


@mcp.tool("get_filing_sections")
def get_filing_sections(identifier: str, accession_number: str, form_type: str):
    """
    Get specific sections from a filing (e.g., business description, risk factors, MD&A).

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The accession number of the filing
        form_type: The type of form (e.g., "10-K", "10-Q")

    Returns:
        Dictionary containing available sections from the filing
    """
    return filings_tools.get_filing_sections(identifier, accession_number, form_type)


# Search Tools
@mcp.tool("search_filings_text")
def search_filings_text(
    keyword: str,
    identifier: str | None = None,
    forms: list | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 25,
    order: str = "asc",
):
    """
    Search across SEC filings for a keyword/phrase with pagination and chronological ordering.

    Args:
        keyword: Search keyword or phrase.
        identifier: Optional company ticker or CIK to filter results.
        forms: Optional list of SEC form types to include (e.g., ["10-K", "8-K"]).
        start_date: Optional start date (YYYY-MM-DD or YYYYMMDD).
        end_date: Optional end date (YYYY-MM-DD or YYYYMMDD).
        page: 1-based page number (default: 1).
        page_size: Results per page (default: 25, max: 100).
        order: "asc" for chronological (default) or "desc".

    Returns:
        Dictionary of search results including total, total_pages, and current page items.
    """
    return search_tools.search_filings_text(
        keyword=keyword,
        identifier=identifier,
        forms=forms,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
        order=order,
    )


# Financial Tools
@mcp.tool("get_financials")
def get_financials(identifier: str, statement_type: str = "all"):
    """
    Get financial statements for a company. USE THIS TOOL when users ask for:
    - Cash flow, cash flow statement, operating cash flow, investing cash flow, financing cash flow
    - Income statement, revenue, net income, earnings, profit/loss, operating income
    - Balance sheet, assets, liabilities, equity, cash and cash equivalents
    - Any financial statement data or financial metrics

    CRITICAL INSTRUCTIONS FOR LLM RESPONSES:
    - ONLY use data from the returned SEC filing. NEVER add external information.
    - ALWAYS include the filing reference information with clickable SEC URL in your response.
    - NEVER estimate, calculate, or interpret data beyond what is explicitly in the filing.
    - PRESERVE EXACT NUMERIC PRECISION - NO ROUNDING! Show exact values like $37,044,000,000 not $37.0B.
    - ALWAYS state the exact filing date and form type when presenting data.
    - Be completely deterministic - same query should always give same response.
    - If data is not in the filing, say "Not available in this filing" - DO NOT guess.

    Args:
        identifier: Company ticker symbol or CIK number
        statement_type: Type of statement ("income", "balance", "cash", or "all")

    Returns:
        Dictionary containing financial statement data extracted directly from SEC EDGAR filings,
        including filing_reference with source URLs and disclaimer.
    """
    return financial_tools.get_financials(identifier, statement_type)


@mcp.tool("get_segment_data")
def get_segment_data(identifier: str, segment_type: str = "geographic"):
    """
    Get revenue breakdown by segments (geographic, product, etc.).

    Args:
        identifier: Company ticker symbol or CIK number
        segment_type: Type of segment analysis (default: "geographic")

    Returns:
        Dictionary containing segment revenue data
    """
    return financial_tools.get_segment_data(identifier, segment_type)


@mcp.tool("get_key_metrics")
def get_key_metrics(identifier: str, metrics: list = None):
    """
    Get key financial metrics for a company.

    Args:
        identifier: Company ticker symbol or CIK number
        metrics: List of specific metrics to retrieve (optional)

    Returns:
        Dictionary containing requested financial metrics
    """
    return financial_tools.get_key_metrics(identifier, metrics)


@mcp.tool("compare_periods")
def compare_periods(identifier: str, metric: str, start_year: int, end_year: int):
    """
    Compare a financial metric across different time periods.

    Args:
        identifier: Company ticker symbol or CIK number
        metric: The financial metric to compare (e.g., "Revenues", "NetIncomeLoss")
        start_year: Starting year for comparison
        end_year: Ending year for comparison

    Returns:
        Dictionary containing period comparison data and growth analysis
    """
    return financial_tools.compare_periods(identifier, metric, start_year, end_year)


@mcp.tool("discover_company_metrics")
def discover_company_metrics(identifier: str, search_term: str = None):
    """
    Discover available financial metrics for a company.

    Args:
        identifier: Company ticker symbol or CIK number
        search_term: Optional search term to filter metrics

    Returns:
        Dictionary containing list of available metrics
    """
    return financial_tools.discover_company_metrics(identifier, search_term)


@mcp.tool("get_xbrl_concepts")
def get_xbrl_concepts(identifier: str, accession_number: str = None, concepts: list = None, form_type: str = "10-K"):
    """
    ADVANCED TOOL: Extract specific XBRL concepts from a filing.

    DO NOT USE for general financial data requests. Use get_financials() instead for:
    - Cash flow statements, income statements, balance sheets
    - Revenue, net income, assets, liabilities, cash data

    CRITICAL INSTRUCTIONS FOR LLM RESPONSES:
    - ONLY report values found in the specific SEC filing. NEVER add context from other sources.
    - ALWAYS include the filing reference information with clickable SEC URL (date, accession number, SEC URL).
    - NEVER estimate or calculate values not explicitly present in the filing.
    - PRESERVE EXACT NUMERIC PRECISION - NO ROUNDING! Show exact values like $37,044,000,000 not $37.0B.
    - ALWAYS specify the exact period/context for each value from the filing.
    - Be completely deterministic - identical queries must give identical responses.
    - If a concept is not found in the filing, state "Not found in this filing" - DO NOT guess.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: Optional specific filing accession number
        concepts: Optional list of specific concepts to extract (e.g., ["Revenues", "Assets"])
        form_type: Form type if no accession number provided (default: "10-K")

    Returns:
        Dictionary containing extracted XBRL concepts with filing_reference and source URLs.
    """
    return financial_tools.get_xbrl_concepts(identifier, accession_number, concepts, form_type)


@mcp.tool("discover_xbrl_concepts")
def discover_xbrl_concepts(
    identifier: str, accession_number: str = None, form_type: str = "10-K", namespace_filter: str = None
):
    """
    Discover all available XBRL concepts in a filing, including company-specific ones.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: Optional specific filing accession number
        form_type: Form type if no accession number provided (default: "10-K")
        namespace_filter: Optional filter to show only concepts from specific namespace

    Returns:
        Dictionary containing all discovered XBRL concepts, namespaces, and company-specific tags
    """
    return financial_tools.discover_xbrl_concepts(identifier, accession_number, form_type, namespace_filter)








# Utility Tools
@mcp.tool("get_recommended_tools")
def get_recommended_tools(form_type: str):
    """
    Get recommended tools for analyzing specific form types.

    Args:
        form_type: The SEC form type (e.g., "10-K", "8-K", "4")

    Returns:
        Dictionary containing recommended tools and usage tips
    """
    recommendations = {
        "10-K": {
            "tools": ["get_financials", "get_filing_sections", "get_segment_data", "get_key_metrics"],
            "description": "Annual report with comprehensive business and financial information",
            "tips": [
                "Use get_financials to extract financial statements",
                "Use get_filing_sections to read business description and risk factors",
                "Use get_segment_data for geographic/product revenue breakdown",
            ],
        },
        "10-Q": {
            "tools": ["get_financials", "get_filing_sections", "compare_periods"],
            "description": "Quarterly report with unaudited financial statements",
            "tips": [
                "Use get_financials for quarterly financial data",
                "Use compare_periods to analyze quarter-over-quarter trends",
            ],
        },
        "8-K": {
            "tools": ["analyze_8k", "get_filing_content"],
            "description": "Current report for material events",
            "tips": [
                "Use analyze_8k to identify specific events reported",
                "Check for press releases and material agreements",
            ],
        },
        "DEF 14A": {
            "tools": ["get_filing_content", "get_filing_sections"],
            "description": "Proxy statement with executive compensation and governance",
            "tips": ["Look for executive compensation tables", "Review shareholder proposals and board information"],
        },
    }

    form_type_upper = form_type.upper()
    if form_type_upper in recommendations:
        return {"success": True, "form_type": form_type_upper, "recommendations": recommendations[form_type_upper]}
    else:
        return {
            "success": True,
            "form_type": form_type_upper,
            "message": "No specific recommendations available for this form type",
            "general_tools": ["get_filing_content", "get_recent_filings"],
        }


# Manifest + Dispatcher
def _build_tool_manifest() -> Dict[str, Any]:
    """Build a JSON-serializable manifest of available tools using signatures/docstrings.

    Returns:
        dict with keys: tools (list), count (int)
    """
    tools = []
    for name in TOOL_NAMES:
        func = globals().get(name)
        if not callable(func):
            continue
        try:
            sig = inspect.signature(func)
        except Exception:
            sig = None
        params = []
        if sig:
            for p in sig.parameters.values():
                # Only expose simple metadata for readability
                default = None if p.default is inspect._empty else p.default
                annotation = None if p.annotation is inspect._empty else p.annotation
                ann_str = None
                try:
                    ann_str = annotation.__name__  # type: ignore[attr-defined]
                except Exception:
                    ann_str = str(annotation) if annotation is not None else None
                params.append(
                    {
                        "name": p.name,
                        "kind": str(p.kind),
                        "type": ann_str,
                        "default": default,
                    }
                )
        tools.append(
            {
                "name": name,
                "description": (globals().get(name).__doc__ or "").strip(),
                "parameters": params,
            }
        )
    return {"tools": tools, "count": len(tools)}


def _score_tool_match(description: str, tool: Dict[str, Any]) -> int:
    """Very simple keyword overlap scoring between description and tool metadata.

    KISS: tokenize on words, overlap name + description. No external deps.
    """
    text = f"{tool.get('name','')} {(tool.get('description') or '')}"
    to_words = lambda s: set(re.findall(r"[A-Za-z0-9_]+", s.lower()))
    d_words = to_words(description)
    t_words = to_words(text)
    # Heavier weight on exact tool-name token hits
    name_words = to_words(tool.get("name", ""))
    return len(d_words & t_words) + 2 * len(d_words & name_words)


def _call_tool_safely(func, provided: Dict[str, Any]) -> Dict[str, Any]:
    """Call a tool by filtering kwargs to its signature and returning JSON error on failure."""
    try:
        sig = inspect.signature(func)
        allowed = {p.name for p in sig.parameters.values()}
        filtered = {k: v for k, v in (provided or {}).items() if k in allowed}
        result = func(**filtered)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool("list_tools")
def list_tools():
    """
    Return a JSON manifest of available MCP tools including names, descriptions, and parameters.

    Use this to inspect capabilities before choosing a tool.
    """
    try:
        return _build_tool_manifest()
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool("dispatch_tool")
def dispatch_tool(description: str, arguments: dict | None = None, dry_run: bool = False):
    """
    Choose and (optionally) invoke the best tool based on a natural-language description.

    Args:
        description: Natural-language description of the intent (e.g., "get latest 10-K financials for NVDA").
        arguments: Optional dict of arguments to pass to the chosen tool (only matching params are used).
        dry_run: If True, do not execute; only return selected tool and its signature.

    Returns:
        On success: { success, selected_tool, score, dry_run, (result|signature) }
        On error:   { success: False, error }
    """
    try:
        manifest = _build_tool_manifest()
        tools = manifest.get("tools", [])
        if not tools:
            return {"success": False, "error": "No tools available"}

        scored = [
            (t, _score_tool_match(description, t))
            for t in tools
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        best, score = scored[0]

        name = best["name"]
        func = globals().get(name)
        if not callable(func):
            return {"success": False, "error": f"Selected tool '{name}' is not callable"}

        if dry_run:
            return {
                "success": True,
                "selected_tool": name,
                "score": score,
                "dry_run": True,
                "signature": best,
            }

        return {
            "success": True,
            "selected_tool": name,
            "score": score,
            "dry_run": False,
            **_call_tool_safely(func, arguments or {}),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="SEC EDGAR MCP Server - Access SEC filings and financial data")
    parser.add_argument("--transport", default=None, help="Transport method: stdio or http")
    parser.add_argument("--host", default=None, help="HTTP host (when using http transport)")
    parser.add_argument("--port", default=None, help="HTTP port (when using http transport)")
    args = parser.parse_args()

    # Transport selection: CLI > TRANSPORT env > infer from PORT env > default stdio
    inferred = "http" if os.getenv("PORT") else None
    transport = (args.transport or os.getenv("TRANSPORT") or inferred or "stdio").strip().lower()

    if transport == "http":
        global http_app
        if http_app is None:
            # Create streamable HTTP app if available, fallback to basic http app
            try:
                http_app = mcp.streamable_http_app()
            except AttributeError:
                try:
                    http_app = mcp.http_app()
                except Exception as e:
                    raise RuntimeError(
                        "FastMCP HTTP app is unavailable. Please upgrade 'mcp' to a version that supports HTTP."
                    ) from e

            # Add CORS if FastAPI is available; otherwise continue
            try:
                from fastapi.middleware.cors import CORSMiddleware  # type: ignore

                http_app.add_middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
            except Exception:
                pass

            # Add basic root/health routes for platform scanners (FastAPI or Starlette)
            try:
                def _root_fastapi():
                    return {
                        "status": "ok",
                        "name": "SEC EDGAR MCP",
                        "transport": "http",
                        "message": "MCP HTTP server is running",
                    }

                def _healthz_fastapi():
                    return {"status": "ok"}

                add_api_route = getattr(http_app, "add_api_route", None)
                if callable(add_api_route):
                    http_app.add_api_route("/", _root_fastapi, methods=["GET"])  # type: ignore[attr-defined]
                    http_app.add_api_route("/healthz", _healthz_fastapi, methods=["GET"])  # type: ignore[attr-defined]
                else:
                    from starlette.responses import JSONResponse  # type: ignore

                    async def _root_starlette(request):  # type: ignore
                        return JSONResponse(
                            {
                                "status": "ok",
                                "name": "SEC EDGAR MCP",
                                "transport": "http",
                                "message": "MCP HTTP server is running",
                            }
                        )

                    async def _healthz_starlette(request):  # type: ignore
                        return JSONResponse({"status": "ok"})

                    add_route = getattr(http_app, "add_route", None)
                    if callable(add_route):
                        http_app.add_route("/", _root_starlette, methods=["GET"])  # type: ignore[attr-defined]
                        http_app.add_route("/healthz", _healthz_starlette, methods=["GET"])  # type: ignore[attr-defined]
            except Exception:
                pass

        host = (args.host or os.getenv("HOST") or "0.0.0.0").strip()
        port_str = (args.port or os.getenv("PORT") or "8081").strip()
        try:
            port = int(port_str)
        except ValueError:
            port = 8081

        try:
            import uvicorn  # type: ignore
        except Exception as e:
            raise RuntimeError("uvicorn is required for HTTP transport. Install 'uvicorn'.") from e

        uvicorn.run(http_app, host=host, port=port)
    else:
        # Default to stdio transport
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
