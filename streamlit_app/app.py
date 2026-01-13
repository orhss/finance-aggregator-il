"""
Financial Data Aggregator - Streamlit UI
Main entry point for the web application
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state

# Page configuration
st.set_page_config(
    page_title="Financial Data Aggregator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
def load_custom_css():
    """Load custom CSS styling"""
    css = """
    <style>
    /* Main content styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Metric cards styling */
    [data-testid="stMetricValue"] {
        font-size: 28px;
    }

    /* Chart container styling */
    .plotly-graph-div {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Table styling */
    .dataframe {
        font-size: 14px;
    }

    /* Button styling */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
    }

    /* Sidebar styling - theme is set in .streamlit/config.toml */

    /* Hover state for navigation links */
    [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"]:hover {
        background-color: #e1e4e8 !important;
    }

    /* Active/current page styling */
    [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: #0068c9 !important;
    }

    [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] span {
        color: white !important;
    }

    /* Individual navigation items */
    [data-testid="stSidebarNav"] li {
        border-radius: 6px;
        margin: 4px 0;
    }

    /* RTL text support */
    .rtl {
        direction: rtl;
        text-align: right;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Initialize session state
init_session_state()

# Load custom CSS
load_custom_css()

# Main page content
st.title("💰 Financial Data Aggregator")
st.markdown("---")

# Welcome message
st.markdown("""
## Welcome to Your Financial Dashboard

This application provides a comprehensive view of your financial data aggregated from:
- 🏦 Brokers (Excellence, Meitav)
- 🏛️ Pension Funds (Migdal, Phoenix)
- 💳 Credit Cards (CAL, Max, Isracard)

### Getting Started

1. **Configure Credentials**: Use `fin-cli config setup` to securely store your credentials
2. **Sync Data**: Navigate to the **Sync** page to synchronize your financial data
3. **Explore**: Use the navigation menu on the left to explore your data

### Quick Links

- **Dashboard** - High-level overview of your financial status
- **Transactions** - Browse and search all transactions
- **Analytics** - Visual analysis and insights
- **Tags & Rules** - Organize and categorize transactions

---

*Select a page from the sidebar to get started.*
""")

# Quick stats in sidebar if data exists
with st.sidebar:
    st.markdown("### Quick Stats")

    # Try to get basic stats
    try:
        from streamlit_app.utils.session import get_analytics_service
        analytics_service = get_analytics_service()

        if analytics_service:
            # Display quick metrics
            st.metric("Total Balance", "Not yet synced", help="Sync data to see your total balance")
            st.metric("Pending Transactions", "0", help="Transactions awaiting completion")
            st.info("💡 Sync your data to see statistics")
    except Exception as e:
        st.info("💡 Initialize and sync data to see statistics")

    st.markdown("---")
    st.markdown("### About")
    st.caption("Financial Data Aggregator v1.0")
    st.caption("[Documentation](https://github.com) | [Report Issue](https://github.com)")