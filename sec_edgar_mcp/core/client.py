from typing import Optional
from edgar import Company, set_identity, find_company
from ..utils.cache import TickerCache
from ..utils.exceptions import CompanyNotFoundError
from ..config import initialize_config


class EdgarClient:
    """Wrapper around edgar-tools for consistent API access."""

    def __init__(self):
        self._user_agent = initialize_config()
        # Set identity for edgar-tools
        set_identity(self._user_agent)
        self._ticker_cache = TickerCache(self._user_agent)

    def get_company(self, identifier: str) -> Company:
        """Get a Company object by ticker or CIK."""
        try:
            # First try as CIK (if it's all digits)
            if identifier.isdigit() or (identifier.startswith("000") and len(identifier) == 10):
                return Company(identifier)

            # For tickers, always convert to CIK first
            cik = self.get_cik_by_ticker(identifier)
            if cik:
                return Company(cik)

            # Last resort - try direct lookup
            return Company(identifier)
        except Exception:
            raise CompanyNotFoundError(f"Company '{identifier}' not found")

    def get_cik_by_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK by ticker symbol."""
        # Try the cache first
        cik = self._ticker_cache.get_cik(ticker)
        if cik:
            return str(cik).zfill(10)

        # Try to get via Company object
        try:
            company = Company(ticker)
            return company.cik
        except Exception:
            return None

    def search_companies(self, query: str, limit: int = 10) -> list:
        """Search for companies by name."""
        try:
            # Use edgartools find_company functionality
            search_results = find_company(query)
            
            companies = []
            if search_results:
                # Handle different result types from find_company
                if hasattr(search_results, '__iter__') and not isinstance(search_results, str):
                    # Multiple results
                    for result in list(search_results)[:limit]:
                        if hasattr(result, 'cik'):
                            companies.append({
                                "cik": str(result.cik).zfill(10), 
                                "name": getattr(result, 'name', str(result)), 
                                "tickers": getattr(result, "tickers", [])
                            })
                else:
                    # Single result
                    if hasattr(search_results, 'cik'):
                        companies.append({
                            "cik": str(search_results.cik).zfill(10), 
                            "name": getattr(search_results, 'name', str(search_results)), 
                            "tickers": getattr(search_results, "tickers", [])
                        })

            return companies
        except Exception:
            # Fallback: try direct company lookup by ticker
            try:
                company = Company(query)
                if hasattr(company, 'cik'):
                    return [{"cik": str(company.cik).zfill(10), "name": getattr(company, 'name', query), "tickers": [query]}]
            except Exception:
                pass

            return []
