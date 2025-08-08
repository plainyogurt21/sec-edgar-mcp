# SEC EDGAR MCP Server - Cline Setup Guide

This guide will help you integrate the SEC EDGAR MCP server with the Cline VS Code extension for powerful AI-driven SEC filing analysis.

## Prerequisites

- VS Code with Cline extension installed
- Python 3.11+ 
- SEC EDGAR MCP server installed (`pip install sec-edgar-mcp`)

## Installation Methods

### Method 1: Using Cline MCP Marketplace (Recommended)

1. Open VS Code with Cline extension
2. In the Cline pane, click the MCP Servers icon (📋) in the top navigation bar
3. Click the "Extensions" button (square icon) to access the MCP marketplace
4. Search for "SEC EDGAR MCP" and click "Install"

### Method 2: Manual Configuration

1. In Cline, click the MCP Servers icon and select "Configure MCP Servers"
2. Add this configuration:

```json
{
  "mcpServers": {
    "sec-edgar-mcp": {
      "command": "python",
      "args": ["-m", "sec_edgar_mcp.server"],
      "env": {
        "EDGAR_USER_AGENT": "Adu Subramanian (1wholepackage@gmail.com)"
      },
      "alwaysAllow": [
        "get_company_info",
        "get_recent_filings", 
        "get_financials",
        "get_insider_transactions"
      ],
      "disabled": false
    }
  }
}
```

## Available Tools

The SEC EDGAR MCP server provides 22 comprehensive tools across 4 categories:

### Company Tools (4)
- `get_cik_by_ticker` - Get CIK number by ticker symbol
- `get_company_info` - Get detailed company information from SEC records
- `search_companies` - Search companies by name
- `get_company_facts` - Get key company financial facts

### Filing Tools (4)
- `get_recent_filings` - Get recent SEC filings
- `get_filing_content` - Get content of specific filings
- `analyze_8k` - Analyze 8-K filings for events
- `get_filing_sections` - Extract specific sections from filings

### Financial Tools (8)
- `get_financials` - Get financial statements (income, balance, cash flow)
- `get_segment_data` - Get revenue by geographic/product segments
- `get_key_metrics` - Get key financial metrics
- `compare_periods` - Compare metrics across time periods
- `discover_company_metrics` - Find available financial metrics
- `get_xbrl_concepts` - Extract specific XBRL concepts (advanced)
- `discover_xbrl_concepts` - Find available XBRL concepts
- `get_recommended_tools` - Get tool recommendations by form type

### Insider Trading Tools (5)
- `get_insider_transactions` - Get insider trading transactions
- `get_insider_summary` - Get summary of insider activity
- `get_form4_details` - Get detailed Form 4 information
- `analyze_form4_transactions` - Analyze Form 4 transactions in detail
- `analyze_insider_sentiment` - Analyze insider trading sentiment

## Usage Examples

Once configured, you can ask Cline questions like:

### Company Research
```
"What's Apple's latest 10-K filing information?"
"Get Tesla's recent quarterly filings"
"Find companies related to 'artificial intelligence'"
```

### Financial Analysis
```
"Show me NVIDIA's latest financial statements"
"Compare Microsoft's revenue over the last 3 years" 
"What are Amazon's key financial metrics?"
```

### Insider Trading Analysis
```
"Get recent insider transactions for Meta"
"Analyze Form 4 filings for Google in the last 60 days"
"Show me insider trading sentiment for Tesla"
```

### Filing Analysis
```
"Analyze the latest 8-K filing for Apple"
"Get the business description section from Tesla's 10-K"
"What events are reported in Microsoft's recent 8-K?"
```

## Configuration Options

### User Agent (Recommended)
The SEC requires a proper user agent for API requests. Set this in your configuration:

```json
"env": {
  "EDGAR_USER_AGENT": "Adu Subramanian (1wholepackage@gmail.com)"
}
```

### Always Allow Tools
For faster workflow, specify commonly used tools in `alwaysAllow`:

```json
"alwaysAllow": [
  "get_company_info",
  "get_recent_filings",
  "get_financials",
  "analyze_8k",
  "get_insider_transactions"
]
```

## MCP Rules for Smart Activation

Create a `.clinerules` file in your project to automatically activate SEC EDGAR tools:

```json
{
  "mcpRules": {
    "secResearch": {
      "servers": ["sec-edgar-mcp"],
      "triggers": [
        "sec", "edgar", "filing", "10-k", "10-q", "8-k", 
        "financial", "earnings", "revenue", "insider", 
        "form 4", "cik", "ticker", "company info"
      ],
      "description": "SEC EDGAR filing research and financial analysis"
    }
  }
}
```

## Troubleshooting

### Server Won't Start
- Check Python version: `python --version` (needs 3.11+)
- Verify installation: `pip show sec-edgar-mcp`
- Check logs in Cline MCP server panel

### API Rate Limits
- The SEC EDGAR API has rate limits (10 requests/second)
- The server handles rate limiting automatically
- Use a proper user agent as shown above

### Missing Data
- Not all companies have all types of data
- Recent filings may take time to appear in EDGAR
- Some older filings may have limited XBRL data

### Tool Permissions
- If tools are being blocked, add them to `alwaysAllow`
- Restart the MCP server after configuration changes
- Check MCP server status in Cline panel

## Best Practices

1. **Use Specific Queries**: Instead of "tell me about Apple", ask "get Apple's latest 10-K filing"
2. **Specify Time Periods**: "Get Tesla's filings from the last 30 days"
3. **Request Exact Data**: Ask for specific financial statement items or sections
4. **Verify Data**: The server provides SEC URLs for all data - use them to verify
5. **Batch Related Queries**: Ask for multiple related items in one request

## Support

- Server Issues: [GitHub Issues](https://github.com/stefanoamorelli/sec-edgar-mcp/issues)
- Documentation: [SEC EDGAR MCP Docs](https://sec-edgar-mcp.amorelli.tech/)
- Cline Extension: [Cline Documentation](https://docs.cline.bot/)

## Advanced Features

### Custom Financial Metrics
Use `discover_company_metrics` to find available metrics, then request specific ones:

```
"Discover available financial metrics for Microsoft"
"Get Microsoft's 'OperatingIncomeLoss' metric for the last 3 years"
```

### XBRL Concept Extraction
For advanced users, extract specific XBRL concepts:

```
"Get XBRL concepts for Tesla's latest 10-K focusing on revenue items"
"Extract specific balance sheet concepts from Apple's filing"
```

### Cross-Company Analysis
Compare metrics across multiple companies:

```
"Compare revenue growth between Apple, Microsoft, and Google over 3 years"
"Analyze insider trading activity for top 5 tech companies"
```

---

**Note**: This MCP server provides deterministic, exact data from SEC EDGAR filings with no external analysis or interpretation. All responses include filing references and SEC URLs for independent verification.