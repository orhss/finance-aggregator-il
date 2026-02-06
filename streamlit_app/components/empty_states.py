"""
Empty States Component

Provides welcoming empty states for pages with no data.
Follows financial app UX best practices: helpful guidance, not just warnings.
"""

import streamlit as st


def empty_transactions_state():
    """Welcoming empty state for transactions page"""
    st.markdown("""
    <div style='text-align: center; padding: 3rem 0;'>
        <h2>📭 No Transactions Yet</h2>
        <p style='font-size: 1.1rem; color: #666; margin: 1.5rem 0;'>
            Let's get your financial data synced so you can see your transactions here.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        **Quick Start Guide:**
        1. Configure your credentials: `fin-cli config setup`
        2. Click the button below to sync your accounts
        3. Come back here to see your transactions
        """)

        if st.button("🔄 Start Syncing", type="primary", width="stretch", key="empty_txn_sync"):
            st.switch_page("views/accounts.py")

        st.caption("⏱️ First sync usually takes 2-3 minutes")


def empty_search_results(filter_count: int = 0):
    """Empty state when filters return no results"""
    st.info(f"""
    🔍 No transactions match your {filter_count} active filter(s).

    **Try:**
    - Expanding your date range
    - Removing some filters
    - Checking for typos in search terms
    """)

    if st.button("🔄 Clear All Filters", key="clear_filters_empty"):
        # Clear common filter keys from session state
        filter_keys = ['search_input', 'category_filter', 'status_filter', 'tag_filter']
        for key in filter_keys:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


def empty_accounts_state():
    """Empty state for accounts page"""
    st.markdown("""
    <div style='text-align: center; padding: 3rem 0;'>
        <h2>🏦 No Accounts Found</h2>
        <p style='font-size: 1.1rem; color: #666; margin: 1.5rem 0;'>
            You haven't synced any financial accounts yet.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        **Get Started:**

        1. **Set up credentials** using the CLI:
           ```bash
           fin-cli config setup
           ```

        2. **Sync your accounts** to import data:
           ```bash
           fin-cli sync all
           ```

        3. **Or use the UI** - click below to go to the Sync page
        """)

        if st.button("🔄 Go to Sync", type="primary", width="stretch", key="empty_acct_sync"):
            st.switch_page("views/accounts.py")

        st.caption("💡 Tip: Start with one institution to test the setup")


def empty_analytics_state():
    """Empty state for analytics page"""
    st.markdown("""
    <div style='text-align: center; padding: 3rem 0;'>
        <h2>📊 No Data to Analyze</h2>
        <p style='font-size: 1.1rem; color: #666; margin: 1.5rem 0;'>
            Analytics require transaction data. Let's get you set up!
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        **What You'll Get:**
        - 📈 Spending trends over time
        - 🎯 Category breakdowns
        - 📅 Monthly comparisons
        - 💡 Smart insights

        **Next Steps:**
        1. Sync your financial accounts
        2. Return here to see your analytics
        """)

        if st.button("🔄 Sync Now", type="primary", width="stretch", key="empty_analytics_sync"):
            st.switch_page("views/accounts.py")


def empty_dashboard_state():
    """Empty state for dashboard page"""
    st.markdown("""
    <div style='text-align: center; padding: 3rem 0;'>
        <h2>👋 Welcome to Your Financial Dashboard!</h2>
        <p style='font-size: 1.1rem; color: #666; margin: 1.5rem 0;'>
            Your dashboard will show your financial overview once you sync your accounts.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        **What You'll See Here:**
        - 💰 Net worth and account balances
        - 📊 Spending patterns and trends
        - 💳 Recent transactions
        - 📈 Financial insights

        **Get Started in 2 Steps:**
        1. Configure your financial institution credentials
        2. Sync your accounts to import data
        """)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("⚙️ Configure", width="stretch", key="empty_dash_config"):
                st.info("💻 Run `fin-cli config setup` in your terminal to configure credentials")

        with col_b:
            if st.button("🔄 Sync", type="primary", width="stretch", key="empty_dash_sync"):
                st.switch_page("views/accounts.py")

        st.caption("🔒 Your data is encrypted and stored locally - we never send it to the cloud")


def empty_category_results():
    """Empty state when no transactions in a category"""
    st.info("""
    📂 No transactions found in this category.

    **This could mean:**
    - No transactions have been categorized yet
    - Try selecting a different category
    - Use the Tags page to categorize transactions
    """)


def no_data_in_date_range():
    """Empty state when date range has no data"""
    st.warning("""
    📅 No transactions found in the selected date range.

    **Try:**
    - Expanding your date range
    - Checking if you have data for this period
    - Syncing more historical data
    """)

    st.caption("💡 Tip: You can adjust the sync date range in Settings")