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
    ) -> ToolResponse:
        """Get recent filings for a company or across all companies."""
        try:
            if identifier:
                # Company-specific filings
                company = self.client.get_company(identifier)
                if form_type is not None:
                    filings = company.get_filings(form=form_type)
                else:
                    filings = company.get_filings()
            else:
                # Global filings using edgartools get_filings()
                filings = get_filings(form=form_type)

            # Limit results
            filings_list = []
            for i, filing in enumerate(filings):
                if i >= limit:
                    break

                # Convert date fields to datetime objects if they're strings
                filing_date = filing.filing_date
                if isinstance(filing_date, str):
                    filing_date = datetime.fromisoformat(filing_date.replace("Z", "+00:00"))

                acceptance_datetime = getattr(filing, "acceptance_datetime", None)
                if isinstance(acceptance_datetime, str):
                    acceptance_datetime = datetime.fromisoformat(acceptance_datetime.replace("Z", "+00:00"))

                period_of_report = getattr(filing, "period_of_report", None)
                if isinstance(period_of_report, str):
                    period_of_report = datetime.fromisoformat(period_of_report.replace("Z", "+00:00"))

                filing_info = FilingInfo(
                    accession_number=filing.accession_number,
                    filing_date=filing_date,
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

    def analyze_8k(
        self, identifier: str, accession_number: str
    ) -> Dict[str, Union[bool, str, Dict[str, Any]]]:
        """Analyze an 8-K filing for specific events."""
        import time
        import logging
        logging.basicConfig(filename="sec_edgar_mcp_analyze8k.log", level=logging.DEBUG)
        try:
            start_total = time.time()
            logging.debug(f"[DEBUG] analyze_8k: Start for {identifier}, accession: {accession_number}")

            start_company = time.time()
            company = self.client.get_company(identifier)
            logging.debug(f"[DEBUG] analyze_8k: company.get_company() took {time.time() - start_company:.2f}s")

            start_filings = time.time()
            filing = None
            for f in company.get_filings(form="8-K"):
                if f.accession_number.replace("-", "") == accession_number.replace("-", ""):
                    filing = f
                    break
            logging.debug(f"[DEBUG] analyze_8k: company.get_filings() loop took {time.time() - start_filings:.2f}s")

            if not filing:
                logging.debug(f"[DEBUG] analyze_8k: Filing not found, total time: {time.time() - start_total:.2f}s")
                raise FilingNotFoundError(f"8-K filing {accession_number} not found")

            start_obj = time.time()
            eightk = filing.obj()
            logging.debug(f"[DEBUG] analyze_8k: filing.obj() took {time.time() - start_obj:.2f}s")
            logging.debug(f"[DEBUG] analyze_8k: Successfully parsed 8-K object: {type(eightk)}")

            raw_date = getattr(eightk, "date_of_report", None)
            formatted_date = None
            if isinstance(raw_date, datetime):
                formatted_date = raw_date.isoformat()
            elif isinstance(raw_date, str):
                try:
                    formatted_date = datetime.fromisoformat(
                        raw_date.replace("Z", "+00:00")
                    ).isoformat()
                except ValueError:
                    formatted_date = raw_date

            analysis: Dict[str, Any] = {
                "date_of_report": formatted_date,
                "items": getattr(eightk, "items", []),
                "events": {},
            }

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
                    analysis["events"][item_code] = {
                        "present": True,
                        "description": description,
                    }

            if hasattr(eightk, "has_press_release"):
                analysis["has_press_release"] = eightk.has_press_release
                if eightk.has_press_release and hasattr(eightk, "press_releases"):
                    press_releases = eightk.press_releases
                    if hasattr(press_releases, 'attachments') and press_releases.attachments:
                        analysis["press_releases"] = []
                        for att in press_releases.attachments:
                            analysis["press_releases"].append({"description": att.description, "content": att.text()})

            if hasattr(eightk, "items") and eightk.items:
                analysis["item_details"] = {}
                for item_name in eightk.items:
                    item_attr = f"item_{item_name.lower().replace('.', '_')}"
                    if hasattr(eightk, item_attr):
                        analysis["item_details"][item_name] = getattr(eightk, item_attr).text

            print(f"Analysis complete: {analysis}")
            return {"success": True, "analysis": analysis}
        except FilingNotFoundError as e:
            print(f"Filing not found error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print(f"An unexpected error occurred in analyze_8k: {e}")
            return {"success": False, "error": f"Failed to analyze 8-K: {e}"}

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
