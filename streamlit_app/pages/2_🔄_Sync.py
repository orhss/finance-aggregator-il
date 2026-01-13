"""
Sync Management Page (Placeholder for Phase 2)
"""

import streamlit as st

st.set_page_config(
    page_title="Sync - Financial Aggregator",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 Sync Management")
st.markdown("---")

st.info("🚧 This page is under construction and will be implemented in Phase 2.")

st.markdown("""
### Coming Soon

This page will allow you to:
- View sync status for all institutions
- Trigger manual synchronization
- Configure sync options (headless mode, date ranges)
- View sync history and logs

### For Now

Use the CLI to sync your data:

```bash
# Sync all institutions
fin-cli sync all

# Sync specific institution
fin-cli sync cal
fin-cli sync excellence
fin-cli sync migdal
```
""")

if st.button("← Back to Dashboard"):
    st.switch_page("pages/1_📊_Dashboard.py")
