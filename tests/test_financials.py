import unittest
from sec_edgar_mcp.tools.financial import FinancialTools

class TestFinancials(unittest.TestCase):
    def test_bbio_all_financials(self):
        tools = FinancialTools()
        result = tools.get_financials("BBIO", statement_type="all")
        print("Full result:", result)
        self.assertTrue(result["success"])
        self.assertIn("statements", result)
        for stmt_type, stmt_data in result["statements"].items():
            print(f"\nStatement type: {stmt_type}")
            for key, value in stmt_data.items():
                print(f"  {key}: {value}")

if __name__ == "__main__":
    unittest.main()
