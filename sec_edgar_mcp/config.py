import os


def initialize_config():
    """Initialize the SEC EDGAR configuration"""
    # Try both environment variable names for compatibility
    sec_edgar_user_agent = os.getenv("EDGAR_USER_AGENT") or os.getenv("SEC_EDGAR_USER_AGENT")
    if not sec_edgar_user_agent:
        # Provide a default user agent if none is set
        sec_edgar_user_agent = "Adu Subramanian (1wholepackage@gmail.com)"

    return sec_edgar_user_agent
