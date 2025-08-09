import unittest

from sec_edgar_mcp.tools.financial import FinancialTools


class TestIncomeStatement(unittest.TestCase):
    def test_bbio_income_statement_complete(self):
        """Ensure we can retrieve a reasonably complete income statement for BBIO."""
        tools = FinancialTools()
        result = tools.get_financials("BBIO", statement_type="income")

        # If we cannot access network or EDGAR, skip to avoid false failures
        if not result.get("success"):
            self.skipTest(f"Skipping due to retrieval failure: {result}")

        # Basic success and structure checks
        self.assertIn("statements", result)
        self.assertIn("income_statement", result["statements"])

        income = result["statements"]["income_statement"]

        # Prefer the DataFrame-shaped payload when available
        if all(k in income for k in ("data", "columns", "index")):
            # Ensure it looks like a full statement, not a stub
            self.assertIsInstance(income["index"], list)
            self.assertIsInstance(income["columns"], list)
            self.assertGreaterEqual(len(income["index"]), 8)  # reasonable minimum number of rows
            self.assertGreaterEqual(len(income["columns"]), 1)

            # Sanity check for common line items (allow variations)
            idx_lower = [str(x).lower() for x in income["index"]]
            expected_any = [
                "revenue",
                "revenues",
                "gross profit",
                "operating income",
                "operatingincomeloss",
                "net income",
                "netincomeloss",
            ]
            self.assertTrue(
                any(any(token in i for token in expected_any) for i in idx_lower),
                msg=f"Expected common income statement lines missing. Index: {income['index']}",
            )
        else:
            # Fallback shapes: xbrl_statement or dynamically discovered concepts
            # Just assert non-empty content was retrieved.
            self.assertTrue(income)


if __name__ == "__main__":
    unittest.main()

