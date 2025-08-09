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
        try:
            # Get company and find specific filing
            company = self.client.get_company(identifier)
            
            # Normalize accession number for comparison
            target_accession = accession_number.replace("-", "")
            
            # Find the specific 8-K filing
            filing = None
            filings = company.get_filings(form="8-K")
            
            # Limit search to reasonable number to avoid timeout
            count = 0
            for f in filings:
                if count >= 100:  # Limit search to prevent timeout
                    break
                if f.accession_number.replace("-", "") == target_accession:
                    filing = f
                    break
                count += 1

            if not filing:
                raise FilingNotFoundError(f"8-K filing {accession_number} not found")

            # Parse the 8-K filing with timeout protection
            try:
                eightk = filing.obj()
            except Exception as e:
                return {"success": False, "error": f"Failed to parse filing: {str(e)}"}

            # Format date of report
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

            # Build analysis structure
            analysis: Dict[str, Any] = {
                "date_of_report": formatted_date,
                "items": getattr(eightk, "items", []),
                "events": {},
                "accession_number": filing.accession_number,
                "filing_date": filing.filing_date.isoformat() if hasattr(filing.filing_date, 'isoformat') else str(filing.filing_date),
                "url": getattr(filing, "url", None)
            }

            # Map of 8-K item codes to descriptions
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

            # Check for specific items
            for item_code, description in item_descriptions.items():
                if hasattr(eightk, "has_item") and eightk.has_item(item_code):
                    analysis["events"][item_code] = {
                        "present": True,
                        "description": description,
                    }

            # Check for press releases
            if hasattr(eightk, "has_press_release"):
                analysis["has_press_release"] = eightk.has_press_release
                if eightk.has_press_release and hasattr(eightk, "press_releases"):
                    press_releases = eightk.press_releases
                    if hasattr(press_releases, 'attachments') and press_releases.attachments:
                        analysis["press_releases"] = []
                        for att in press_releases.attachments:
                            # Limit press release content to prevent response size issues
                            content = att.text()
                            if len(content) > 10000:
                                content = content[:10000] + "... [truncated]"
                            analysis["press_releases"].append({
                                "description": att.description, 
                                "content": content
                            })

            # Extract item details
            if hasattr(eightk, "items") and eightk.items:
                analysis["item_details"] = {}
                for item_name in eightk.items:
                    item_attr = f"item_{item_name.lower().replace('.', '_')}"
                    if hasattr(eightk, item_attr):
                        item_text = getattr(eightk, item_attr).text
                        # Limit item text to prevent response size issues
                        if len(item_text) > 5000:
                            item_text = item_text[:5000] + "... [truncated]"
                        analysis["item_details"][item_name] = item_text

            return {"success": True, "analysis": analysis}
            
        except FilingNotFoundError as e:
            return {"success": False, "error": str(e)}
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
