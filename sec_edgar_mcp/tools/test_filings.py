import sys
from sec_edgar_mcp.tools.filings import FilingsTools

def test_analyze_8k():
    # Example: BBIO, accession number from recent filings
    identifier = "BBIO"
    accession_number = "0000950170-25-102985"
    filings_tools = FilingsTools()
    result = filings_tools.analyze_8k(identifier, accession_number)
    print("analyze_8k result:", result)

if __name__ == "__main__":
    test_analyze_8k()
