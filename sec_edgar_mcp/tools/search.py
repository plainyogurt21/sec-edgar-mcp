from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Union
from datetime import datetime

from ..core.client import EdgarClient
from .types import ToolResponse


def _to_date(value: Optional[Union[str, datetime]]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Accept YYYY-MM-DD or YYYYMMDD
    try:
        if isinstance(value, str) and len(value) == 8 and value.isdigit():
            return datetime.strptime(value, "%Y%m%d")
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


class SearchTools:
    """Tools for keyword search across SEC filings.

    This integrates with edgartools text search where available and returns
    results in chronological order with simple pagination.
    """

    def __init__(self):
        self.client = EdgarClient()
        # Try to import TextSearch lazily and defensively
        try:
            from edgar.search.textsearch import TextSearch as _TS  # type: ignore

            self._text_search_cls = _TS
        except Exception:
            self._text_search_cls = None

    def _iter_results(
        self,
        keyword: str,
    ) -> Iterable[Any]:
        """Create an iterator of text search results using edgartools if available."""
        if not self._text_search_cls:
            raise RuntimeError(
                "Text search is unavailable: edgartools 'TextSearch' not found. Update edgartools to a version that supports text search."
            )

        try:
            searcher = self._text_search_cls()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize TextSearch: {e}")

        # The edgartools API may vary slightly across versions; prefer a simple call
        # and perform filtering locally for robustness.
        try:
            # Common API: search(query: str) -> Iterable[Match]
            return iter(searcher.search(keyword))  # type: ignore[attr-defined]
        except Exception as e:
            raise RuntimeError(f"Text search failed: {e}")

    def _coerce_result(self, item: Any) -> Optional[Dict[str, Any]]:
        """Normalize a result item from edgartools into a plain dict.

        Attempts to read common attributes while being resilient to API differences.
        """
        try:
            def get_attr(obj: Any, name: str, default: Any = None) -> Any:
                try:
                    return getattr(obj, name)
                except Exception:
                    return default

            # Basic fields expected from edgartools TextSearch results
            accession_number = get_attr(item, "accession_number") or get_attr(item, "accession")
            form_type = get_attr(item, "form") or get_attr(item, "form_type")
            company_name = get_attr(item, "company") or get_attr(item, "company_name")
            cik = get_attr(item, "cik")
            url = get_attr(item, "url") or get_attr(item, "link")
            snippet = get_attr(item, "snippet") or get_attr(item, "context") or ""

            filing_date = get_attr(item, "filing_date") or get_attr(item, "date")
            if isinstance(filing_date, str):
                try:
                    filing_date_dt = datetime.fromisoformat(filing_date.replace("Z", "+00:00"))
                except Exception:
                    # Try compact formats like YYYYMMDD
                    try:
                        filing_date_dt = datetime.strptime(filing_date, "%Y%m%d")
                    except Exception:
                        filing_date_dt = None
            elif isinstance(filing_date, datetime):
                filing_date_dt = filing_date
            else:
                filing_date_dt = None

            # Build normalized dict
            norm = {
                "accession_number": accession_number,
                "filing_date": filing_date_dt.isoformat() if filing_date_dt else None,
                "form_type": form_type,
                "company_name": company_name,
                "cik": str(cik).zfill(10) if cik is not None else None,
                "url": url,
                "snippet": snippet,
            }

            # If we are missing critical identifiers, drop the item
            if not norm["accession_number"] or not norm["filing_date"]:
                return None

            return norm
        except Exception:
            return None

    def search_filings_text(
        self,
        keyword: str,
        identifier: Optional[str] = None,
        forms: Optional[Union[str, List[str]]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
        order: str = "asc",
    ) -> ToolResponse:
        """Search filings text for a keyword with pagination and chronological ordering.

        Args:
            keyword: Search keyword or phrase.
            identifier: Optional company ticker or CIK to filter results.
            forms: Optional single form type or list of form types (e.g., "10-K", ["8-K", "10-Q"]).
            start_date: Optional ISO date (YYYY-MM-DD) or YYYYMMDD to filter from.
            end_date: Optional ISO date (YYYY-MM-DD) or YYYYMMDD to filter to.
            page: 1-based page index for pagination.
            page_size: Number of results per page.
            order: "asc" for chronological (oldest first), "desc" for reverse.

        Returns:
            ToolResponse with keys: success, results, page, total_pages, total, order.
        """
        try:
            if not keyword or not isinstance(keyword, str):
                return {"success": False, "error": "keyword is required and must be a string"}

            page = max(1, int(page))
            page_size = max(1, min(100, int(page_size)))

            # Normalize forms list
            forms_list: Optional[List[str]]
            if forms is None:
                forms_list = None
            elif isinstance(forms, str):
                forms_list = [forms.upper()]
            else:
                forms_list = [str(f).upper() for f in forms]

            # Resolve company filter to CIK if provided
            cik_filter: Optional[str] = None
            if identifier:
                try:
                    company = self.client.get_company(identifier)
                    cik_filter = str(company.cik).zfill(10)
                except Exception:
                    return {"success": False, "error": f"Unable to resolve identifier '{identifier}' to a company"}

            start_dt = _to_date(start_date)
            end_dt = _to_date(end_date)

            # Collect and normalize results
            raw_iter = self._iter_results(keyword)
            normalized: List[Dict[str, Any]] = []

            # Reasonable cap to avoid unbounded memory; can be adjusted
            CAP = 5000
            count = 0
            for item in raw_iter:
                if count >= CAP:
                    break
                norm = self._coerce_result(item)
                if not norm:
                    continue

                # Filter by company
                if cik_filter and norm.get("cik") and norm["cik"] != cik_filter:
                    continue

                # Filter by forms
                if forms_list and norm.get("form_type") and str(norm["form_type"]).upper() not in forms_list:
                    continue

                # Filter by date range
                fdate_str = norm.get("filing_date")
                try:
                    fdate = datetime.fromisoformat(fdate_str) if fdate_str else None
                except Exception:
                    fdate = None

                if start_dt and fdate and fdate < start_dt:
                    continue
                if end_dt and fdate and fdate > end_dt:
                    continue

                normalized.append(norm)
                count += 1

            # Sort by filing_date
            normalized.sort(key=lambda r: r.get("filing_date") or "")
            if str(order).lower() == "desc":
                normalized.reverse()
            order_val = "desc" if str(order).lower() == "desc" else "asc"

            # Paginate
            total = len(normalized)
            total_pages = max(1, (total + page_size - 1) // page_size)
            if page > total_pages:
                page = total_pages
            start = (page - 1) * page_size
            end = min(start + page_size, total)
            page_items = normalized[start:end]

            return {
                "success": True,
                "keyword": keyword,
                "identifier": identifier,
                "forms": forms_list,
                "start_date": start_dt.isoformat() if start_dt else None,
                "end_date": end_dt.isoformat() if end_dt else None,
                "order": order_val,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "results": page_items,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to search filings text: {str(e)}"}

