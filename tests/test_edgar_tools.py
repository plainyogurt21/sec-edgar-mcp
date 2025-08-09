from edgar import Company
from edgar.core import set_identity

set_identity("1wholepackage@gmail.com")

def main():
    company = Company("BBIO")
    filings = company.get_filings()
    from edgar.financials import Financials

    for filing in filings:
        if not filing.form.startswith("10-K") and not filing.form.startswith("10-Q"):
            continue
        financials = Financials.extract(filing)
        if financials is not None:
            print("Income Statement:")
            print(financials.income_statement())

            print("\nBalance Sheet:")
            print(financials.balance_sheet())

            print("\nCashflow Statement:")
            print(financials.cashflow_statement())
            break
    else:
        print("No financial statements found for any filings.")

if __name__ == "__main__":
    main()
