"""
Transactions Browser Page (Placeholder for Phase 2)
"""

import streamlit as st

st.set_page_config(
    page_title="Transactions - Financial Aggregator",
    page_icon="💳",
    layout="wide"
)

st.title("💳 Transactions Browser")
st.markdown("---")

st.info("🚧 This page is under construction and will be implemented in Phase 2.")

st.markdown("""
### Coming Soon

This page will allow you to:
- Browse all transactions with filtering
- Search transaction descriptions
- Filter by date range, account, category, tags
- Edit transaction categories and tags
- Export transactions to CSV

### For Now

Use the CLI to view transactions:

```bash
# List all transactions
fin-cli transactions list

# Filter by institution
fin-cli transactions list --institution cal

# Filter by date range
fin-cli transactions list --from 2024-01-01 --to 2024-03-31
```
""")

if st.button("← Back to Dashboard"):
    st.switch_page("pages/1_📊_Dashboard.py")
