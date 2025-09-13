from __future__ import annotations

from typing import List, Dict, Any

from ..core.client import EdgarClient
from .types import ToolResponse


class ResultsTools:
    """Minimal tools to fetch recent financial-results press releases (8-K/6-K)."""

    def __init__(self) -> None:
        self.client = EdgarClient()

    def get_recent_financial_results(self, identifier: str, count: int = 1) -> ToolResponse:
        """
        Return the most recent financial-results press releases for a company.

        Uses 8-K Item 2.02 + EX-99.* signals and keyword heuristics for 6-K.

        Args:
            identifier: Ticker or CIK
            count: Number of results to return

        Returns:
            { success, results: [ { FilingText, FilingURL, FilingDate, AccessionNumber, FormType } ] }
        """
        try:
            company = self.client.get_company(identifier)

            # Gather recent 8-K and 6-K candidates
            candidates = []
            try:
                candidates.extend(list(company.get_filings(form="8-K").head(max(10, count * 3))))
            except Exception:
                pass
            try:
                candidates.extend(list(company.get_filings(form="6-K").head(max(5, count * 2))))
            except Exception:
                pass

            if not candidates:
                return {"success": True, "results": [], "message": "No recent 8-K/6-K filings found"}

            # Sort most recent first
            try:
                candidates.sort(key=lambda f: getattr(f, "filing_date", ""), reverse=True)
            except Exception:
                pass

            results: List[Dict[str, Any]] = []

            def _has_ex99_press_release(filing) -> bool:
                attachments = getattr(filing, "attachments", None)
                if attachments is not None:
                    try:
                        it = list(attachments)
                    except Exception:
                        it = []
                else:
                    it = []

                if not it and hasattr(filing, "exhibits"):
                    try:
                        it = list(filing.exhibits)
                    except Exception:
                        it = []

                for att in it:
                    try:
                        dtype = (getattr(att, "document_type", "") or "").upper()
                        desc = (getattr(att, "description", "") or "").lower()
                        filename = (getattr(att, "document", "") or "").upper()
                        if "EX-99" in dtype or "EX-99" in filename:
                            return True
                        if any(k in desc for k in ["press release", "earnings", "financial results"]):
                            return True
                    except Exception:
                        continue
                return False

            for filing in candidates:
                if len(results) >= count:
                    break

                form = getattr(filing, "form", "")

                is_result = False
                try:
                    if form == "8-K":
                        try:
                            eightk = filing.obj()
                            items = getattr(eightk, "items", []) or []
                            has_202 = any("2.02" in str(i) for i in items)
                        except Exception:
                            has_202 = False
                        is_result = has_202 and _has_ex99_press_release(filing)
                    elif form == "6-K":
                        try:
                            text = filing.text() or ""
                        except Exception:
                            text = ""
                        low = text.lower()
                        is_result = ("financial results" in low) and ("notice of annual" not in low)
                    else:
                        is_result = False
                except Exception:
                    is_result = False

                if not is_result:
                    continue

                # Build output
                try:
                    text = filing.text() or ""
                except Exception:
                    text = ""

                urls = []
                try:
                    if hasattr(filing, "url") and filing.url:
                        urls.append(filing.url)
                    # canonical sec .txt URL
                    clean_acc = filing.accession_number.replace("-", "")
                    urls.append(f"https://www.sec.gov/Archives/edgar/data/{company.cik}/{clean_acc}/{filing.accession_number}.txt")
                except Exception:
                    pass

                results.append(
                    {
                        "FilingText": text,
                        "FilingURL": list(dict.fromkeys([u for u in urls if u])),
                        "FilingDate": getattr(filing, "filing_date", None),
                        "AccessionNumber": getattr(filing, "accession_number", ""),
                        "FormType": form,
                    }
                )

            return {"success": True, "results": results}
        except Exception as e:
            return {"success": False, "error": f"Failed to fetch financial results: {str(e)}"}

    def get_all_recent_8k(self, identifier: str, count: int = 10) -> ToolResponse:
        """
        Return the most recent 8-K or 6-K filings for a company, regardless of item/type.

        Args:
            identifier: Ticker or CIK
            count: Max number of filings to return

        Returns:
            { success, filings: [ { accession_number, filing_date, form_type, company_name, cik, url } ] }
        """
        try:
            company = self.client.get_company(identifier)

            filings = []
            # Pull recent heads from both 8-K and 6-K, then merge/sort
            try:
                filings.extend(list(company.get_filings(form="8-K").head(max(20, count))))
            except Exception:
                pass
            try:
                filings.extend(list(company.get_filings(form="6-K").head(max(20, count))))
            except Exception:
                pass

            if not filings:
                return {"success": True, "filings": []}

            try:
                filings.sort(key=lambda f: getattr(f, "filing_date", ""), reverse=True)
            except Exception:
                pass

            out = []
            for f in filings[:count]:
                try:
                    out.append(
                        {
                            "accession_number": getattr(f, "accession_number", ""),
                            "filing_date": getattr(f, "filing_date", None),
                            "form_type": getattr(f, "form", ""),
                            "company_name": getattr(f, "company", ""),
                            "cik": str(getattr(f, "cik", "")),
                            "url": getattr(f, "url", None),
                        }
                    )
                except Exception:
                    continue

            return {"success": True, "filings": out}
        except Exception as e:
            return {"success": False, "error": f"Failed to fetch recent 8-K/6-K: {str(e)}"}
