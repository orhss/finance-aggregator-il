"""
Analytics & Reports Page (Placeholder for Phase 3)
"""

import streamlit as st

st.set_page_config(
    page_title="Analytics - Financial Aggregator",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Analytics & Reports")
st.markdown("---")

st.info("🚧 This page is under construction and will be implemented in Phase 3.")

st.markdown("""
### Coming Soon

This page will provide comprehensive analytics including:

**Spending Analysis**
- Category breakdown with interactive charts
- Top merchants
- Spending by day of week

**Trends**
- Monthly spending over time
- Category trends
- Year-over-year comparisons

**Balance & Portfolio**
- Portfolio composition
- Balance history
- Profit/Loss tracking

**Tags Analysis**
- Spending by tag
- Tag distribution
- Tag trends over time

### For Now

Use the CLI to view basic statistics:

```bash
# View spending statistics
fin-cli reports stats

# View category breakdown
fin-cli reports by-category
```
""")

if st.button("← Back to Dashboard"):
    st.switch_page("pages/1_📊_Dashboard.py")
