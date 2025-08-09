from typing import Dict, Union, List, Optional, Any
from datetime import datetime
from edgar import get_filings
from ..core.client import EdgarClient
from ..core.models import FilingInfo
from ..utils.exceptions import FilingNotFoundError
from .types import ToolResponse


class FilingsTools:
    """Tools for filing-related operations."""

    def __init__(self):
        self.client = EdgarClient()

    def get_recent_filings(
        self,
        identifier: Optional[str] = None,
        form_type: Optional[Union[str, List[str]]] = None,
        days: int = 30,
        limit: int = 50,
        year: Optional[Union[int, List[int]]] = None,
        quarter: Optional[Union[int, List[int]]] = None,
    ) -> ToolResponse:
        """Get recent filings for a company or across all companies, with optional date, year, and quarter filtering."""
        try:
            filings = None
            if identifier:
                company = self.client.get_company(identifier)
                filings = company.get_filings(
                    form=form_type,
                    year=year,
                    quarter=quarter,
                )
            else:
                filings = get_filings(form=form_type, year=year, quarter=quarter)

            # Filter by days
            now = datetime.utcnow()
            filtered_filings = []
            for filing in filings:
                filing_date = filing.filing_date
                if isinstance(filing_date, str):
                    filing_date = datetime.fromisoformat(filing_date.replace("Z", "+00:00"))
                if (now - filing_date).days <= days:
                    filtered_filings.append(filing)

            # Limit results
            filings_list = []
            for i, filing in enumerate(filtered_filings):
                if i >= limit:
                    break

                acceptance_datetime = getattr(filing, "acceptance_datetime", None)
                if isinstance(acceptance_datetime, str):
                    acceptance_datetime = datetime.fromisoformat(acceptance_datetime.replace("Z", "+00:00"))

                period_of_report = getattr(filing, "period_of_report", None)
                if isinstance(period_of_report, str):
                    period_of_report = datetime.fromisoformat(period_of_report.replace("Z", "+00:00"))

                filing_info = FilingInfo(
                    accession_number=filing.accession_number,
                    filing_date=filing.filing_date,
                    form_type=filing.form,
                    company_name=filing.company,
                    cik=str(filing.cik),
                    file_number=getattr(filing, "file_number", None),
                    acceptance_datetime=acceptance_datetime,
                    period_of_report=period_of_report,
                )
                filings_list.append(filing_info.to_dict())

            return {"success": True, "filings": filings_list, "count": len(filings_list)}
        except Exception as e:
            return {"success": False, "error": f"Failed to get recent filings: {str(e)}"}

    def get_filing_content(self, identifier: str, accession_number: str, form_type: Optional[str] = None) -> ToolResponse:
        """Get the content of a specific filing."""
        try:
            company = self.client.get_company(identifier)

            # Find the specific filing
            filing = None
            for f in company.get_filings(form=form_type):
                if f.accession_number.replace("-", "") == accession_number.replace("-", ""):
                    filing = f
                    break

            if not filing:
                raise FilingNotFoundError(f"Filing {accession_number} not found")

            # Get filing content
            content = filing.text()

            # For structured filings, get the data object
            filing_data = {}
            try:
                obj = filing.obj()
                if obj:
                    # Extract key information based on filing type
                    if filing.form == "8-K" and hasattr(obj, "items"):
                        filing_data["items"] = obj.items
                        filing_data["has_press_release"] = getattr(obj, "has_press_release", False)
                    elif filing.form in ["10-K", "10-Q"]:
                        filing_data["has_financials"] = True
                    elif filing.form in ["3", "4", "5"]:
                        filing_data["is_ownership"] = True
            except Exception:
                pass

            return {
                "success": True,
                "accession_number": filing.accession_number,
                "form_type": filing.form,
                "filing_date": filing.filing_date.isoformat(),
                "content": content[:50000] if len(content) > 50000 else content,  # Limit size
                "content_truncated": len(content) > 50000,
                "filing_data": filing_data,
                "url": filing.url,
            }
        except FilingNotFoundError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to get filing content: {str(e)}"}

    def analyze_8k(self, identifier: str, accession_number: str) -> ToolResponse:
        """Analyze an 8-K filing and extract full content."""
        try:
            company = self.client.get_company(identifier)

            # Find the specific filing
            filing = None
            for f in company.get_filings(form="8-K"):
                if f.accession_number.replace("-", "") == accession_number.replace("-", ""):
                    filing = f
                    break

            if not filing:
                raise FilingNotFoundError(f"8-K filing {accession_number} not found")

            # Get the 8-K object
            eightk = filing.obj()

            # Handle date formatting safely
            date_of_report = None
            if hasattr(eightk, "date_of_report"):
                raw_date = eightk.date_of_report
                if hasattr(raw_date, 'isoformat'):
                    date_of_report = raw_date.isoformat()
                else:
                    date_of_report = str(raw_date) if raw_date else None

            main_text = filing.text()
            sections = []
            # Main 8-K filing content as first section
            sections.append({
                "type": "8-K",
                "label": "Main Filing",
                "content": main_text[:10000] if len(main_text) > 10000 else main_text,
                "content_truncated": len(main_text) > 10000
            })

            # Add each exhibit/attachment as its own section using attachments API if available
            try:
                attachments_candidates = []

                # Prefer the attachments API from edgartools, with graceful fallbacks
                attachments_obj = getattr(filing, "attachments", None)
                if attachments_obj is not None:
                    # Some versions expose an iterable; others expose .exhibits as a filtered view
                    if hasattr(attachments_obj, "exhibits"):
                        try:
                            attachments_candidates = list(attachments_obj.exhibits)
                        except Exception:
                            # Fall back to iterating the container directly
                            try:
                                attachments_candidates = list(attachments_obj)
                            except Exception:
                                attachments_candidates = []
                    else:
                        try:
                            attachments_candidates = list(attachments_obj)
                        except Exception:
                            attachments_candidates = []

                # Legacy fallback to filing.exhibits if present
                if not attachments_candidates and hasattr(filing, "exhibits"):
                    try:
                        attachments_candidates = list(filing.exhibits)
                    except Exception:
                        attachments_candidates = []

                # Iterate and extract text from each candidate
                for idx, exhibit in enumerate(attachments_candidates):
                    label = (
                        getattr(exhibit, "description", None)
                        or getattr(exhibit, "document_type", None)
                        or getattr(exhibit, "type", None)
                        or getattr(exhibit, "filename", None)
                        or getattr(exhibit, "file", None)
                        or f"Exhibit {idx+1}"
                    )

                    # Extract text content with multiple fallbacks per attachments API
                    exhibit_content = ""
                    try:
                        # Primary: .text method or property
                        text_attr = getattr(exhibit, "text", None)
                        if callable(text_attr):
                            exhibit_content = text_attr() or ""
                        elif isinstance(text_attr, str):
                            exhibit_content = text_attr
                        else:
                            # Some implementations provide .to_text()
                            to_text = getattr(exhibit, "to_text", None)
                            if callable(to_text):
                                exhibit_content = to_text() or ""
                            else:
                                # Fallback: content/content_bytes
                                content_attr = getattr(exhibit, "content", None)
                                if isinstance(content_attr, (bytes, bytearray)):
                                    try:
                                        exhibit_content = content_attr.decode("utf-8", errors="ignore")
                                    except Exception:
                                        exhibit_content = ""
                                elif isinstance(content_attr, str):
                                    exhibit_content = content_attr
                                else:
                                    # Last resort: if .html() exists, strip to text
                                    html_fn = getattr(exhibit, "html", None)
                                    if callable(html_fn):
                                        try:
                                            html = html_fn()
                                            if isinstance(html, str):
                                                # Minimal stripping of tags if BeautifulSoup not guaranteed
                                                import re as _re
                                                exhibit_content = _re.sub(r"<[^>]+>", " ", html)
                                                exhibit_content = _re.sub(r"\s+", " ", exhibit_content).strip()
                                        except Exception:
                                            exhibit_content = ""
                    except Exception:
                        exhibit_content = "[Unable to extract exhibit content]"

                    # Build section entry
                    section_entry = {
                        "type": "exhibit",
                        "label": label,
                        "content": exhibit_content[:100000] if len(exhibit_content) > 100000 else exhibit_content,
                        "content_truncated": len(exhibit_content) > 100000,
                    }

                    # Include URL if available for verification
                    url_val = getattr(exhibit, "url", None)
                    if isinstance(url_val, str):
                        section_entry["url"] = url_val

                    sections.append(section_entry)
            except Exception as e:
                sections.append({
                    "type": "exhibit",
                    "label": "Exhibits Error",
                    "content": f"Error extracting exhibits: {str(e)}",
                    "content_truncated": False,
                })

            analysis: Dict[str, Any] = {
                "filing_info": {
                    "accession_number": filing.accession_number,
                    "filing_date": filing.filing_date.isoformat() if hasattr(filing.filing_date, 'isoformat') else str(filing.filing_date),
                    "company": filing.company,
                    "cik": filing.cik,
                    "url": getattr(filing, "url", None)
                },
                "date_of_report": date_of_report,
                "items": getattr(eightk, "items", []),
                "events": {},
                "sections": sections
            }

            # Check for common 8-K items
            item_descriptions = {
                "1.01": "Entry into Material Agreement",
                "1.02": "Termination of Material Agreement",
                "2.01": "Completion of Acquisition or Disposition",
                "2.02": "Results of Operations and Financial Condition",
                "2.03": "Creation of Direct Financial Obligation",
                "3.01": "Notice of Delisting",
                "4.01": "Changes in Accountant",
                "5.01": "Changes in Control",
                "5.02": "Departure/Election of Directors or Officers",
                "5.03": "Amendments to Articles/Bylaws",
                "7.01": "Regulation FD Disclosure",
                "8.01": "Other Events",
            }

            for item_code, description in item_descriptions.items():
                if hasattr(eightk, "has_item") and eightk.has_item(item_code):
                    analysis["events"][item_code] = {"present": True, "description": description}

            return {"success": True, "analysis": analysis}
        except Exception as e:
            return {"success": False, "error": f"Failed to analyze 8-K: {str(e)}"}

    def get_filing_sections(self, identifier: str, accession_number: str, form_type: str) -> ToolResponse:
        """Get specific sections from a filing."""
        try:
            company = self.client.get_company(identifier)

            # Find the filing
            filing = None
            for f in company.get_filings(form=form_type):
                if f.accession_number.replace("-", "") == accession_number.replace("-", ""):
                    filing = f
                    break

            if not filing:
                raise FilingNotFoundError(f"Filing {accession_number} not found")

            # Get filing object
            filing_obj = filing.obj()

            sections = {}

            # Extract sections based on form type
            if form_type in ["10-K", "10-Q"]:
                # Business sections
                if hasattr(filing_obj, "business"):
                    sections["business"] = str(filing_obj.business)[:10000]

                # Risk factors
                if hasattr(filing_obj, "risk_factors"):
                    sections["risk_factors"] = str(filing_obj.risk_factors)[:10000]

                # MD&A
                if hasattr(filing_obj, "mda"):
                    sections["mda"] = str(filing_obj.mda)[:10000]

                # Financial statements
                if hasattr(filing_obj, "financials"):
                    sections["has_financials"] = True

            return {
                "success": True,
                "form_type": form_type,
                "sections": sections,
                "available_sections": list(sections.keys()),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get filing sections: {str(e)}"}
