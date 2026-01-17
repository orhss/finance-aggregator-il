"""
Analytics & Reports Page - Comprehensive financial insights
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import sys
from pathlib import Path
from typing import Tuple, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state, get_db_session
from streamlit_app.utils.formatters import format_currency, format_number, format_datetime
from streamlit_app.utils.cache import (
    get_transactions_cached,
    get_category_spending_cached,
    get_monthly_trend_cached,
    get_accounts_cached,
    get_tags_cached
)
from streamlit_app.utils.errors import safe_call_with_spinner, ErrorBoundary, show_info
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.empty_states import empty_analytics_state
from streamlit_app.components.loading import contextual_spinner
from streamlit_app.components.charts import (
    spending_donut,
    trend_line,
    category_bar,
    balance_history,
    balance_distribution,
    monthly_trend,
    COLORS,
    CATEGORY_COLORS
)
from streamlit_app.components.heatmap import calendar_heatmap, monthly_heatmap

# Page config
st.set_page_config(
    page_title="Analytics - Financial Aggregator",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
init_session_state()

# Render minimal sidebar
render_minimal_sidebar()

# Page header
st.title("📈 Analytics & Reports")
st.markdown("Comprehensive financial insights and visualizations")
st.markdown("---")


def time_range_selector() -> Tuple[date, date]:
    """
    Render time range selector with quick buttons and custom date picker

    Returns:
        Tuple of (start_date, end_date)
    """
    st.subheader("📅 Time Range")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    today = date.today()
    first_of_month = today.replace(day=1)

    # Quick select buttons
    with col1:
        if st.button("This Month", use_container_width=True):
            st.session_state.date_range = ('this_month', first_of_month, today)

    with col2:
        last_month = first_of_month - timedelta(days=1)
        first_of_last_month = last_month.replace(day=1)
        if st.button("Last Month", use_container_width=True):
            st.session_state.date_range = ('last_month', first_of_last_month, last_month)

    with col3:
        three_months_ago = today - relativedelta(months=3)
        if st.button("Last 3 Months", use_container_width=True):
            st.session_state.date_range = ('3_months', three_months_ago, today)

    with col4:
        six_months_ago = today - relativedelta(months=6)
        if st.button("Last 6 Months", use_container_width=True):
            st.session_state.date_range = ('6_months', six_months_ago, today)

    with col5:
        first_of_year = today.replace(month=1, day=1)
        if st.button("This Year", use_container_width=True):
            st.session_state.date_range = ('this_year', first_of_year, today)

    with col6:
        if st.button("Custom", use_container_width=True):
            st.session_state.date_range = ('custom', None, None)

    # Initialize default if not set
    if 'date_range' not in st.session_state:
        st.session_state.date_range = ('3_months', three_months_ago, today)

    # Custom date picker if custom is selected
    if st.session_state.date_range[0] == 'custom':
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=today - relativedelta(months=3),
                max_value=today,
                key="custom_start_date"
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=today,
                max_value=today,
                min_value=start_date if 'custom_start_date' in st.session_state else None,
                key="custom_end_date"
            )
        return start_date, end_date
    else:
        return st.session_state.date_range[1], st.session_state.date_range[2]


# Load analytics data with caching and error handling
with ErrorBoundary("Failed to load analytics data"):
    from db.database import get_session
    from db.models import Account, Transaction, Balance, Tag, TransactionTag
    from sqlalchemy import func, and_, desc, extract

    # Check if database has data (quick check)
    session = get_session()
    transaction_count = session.query(func.count(Transaction.id)).scalar()
    session.close()

    if not transaction_count or transaction_count == 0:
        empty_analytics_state()
        st.stop()

    # Time range selector
    start_date, end_date = time_range_selector()
    st.info(f"Showing data from **{start_date}** to **{end_date}**")
    st.markdown("---")

    # Fetch transactions for selected period (cached for 5 minutes)
    transactions_list = safe_call_with_spinner(
        get_transactions_cached,
        spinner_text=contextual_spinner("analyzing", "transaction patterns"),
        error_message="Failed to load transaction data",
        default_return=[],
        start_date=start_date,
        end_date=end_date
    )

    # Convert to DataFrame
    transactions_data = []
    for txn in transactions_list:
        txn_date = txn['transaction_date']
        transactions_data.append({
            'id': txn['id'],
            'date': txn_date,
            'amount': txn['original_amount'],
            'category': txn['effective_category'] or 'Uncategorized',
            'description': txn['description'],
            'status': txn['status'],
            'account_id': txn['account_id'],
            'is_expense': txn['original_amount'] < 0,
            'day_of_week': txn_date.strftime('%A') if txn_date else 'Unknown'
        })

    df_all = pd.DataFrame(transactions_data)

    if df_all.empty:
        st.warning("No transactions found in the selected date range.")
        st.stop()

    # Convert date column to datetime for proper .dt accessor usage
    df_all['date'] = pd.to_datetime(df_all['date'])

    # Filter for expenses only (for most charts)
    df_expenses = df_all[df_all['is_expense']].copy()
    # Ensure date column is datetime in df_expenses as well
    df_expenses['date'] = pd.to_datetime(df_expenses['date'])

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Spending Analysis",
        "📈 Trends",
        "💰 Balance & Portfolio",
        "🏷️ Tags Analysis",
        "🔄 Comparisons"
    ])

    # ============================================================================
    # TAB 1: SPENDING ANALYSIS
    # ============================================================================
    with tab1:
        st.header("Spending Analysis")

        if df_expenses.empty:
            st.info("No expenses found in the selected period.")
        else:
            # Row 1: Category Breakdown + Top Merchants
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Category Breakdown")
                fig_category = spending_donut(
                    df_expenses,
                    title="Spending by Category",
                    value_col="amount",
                    label_col="category",
                    top_n=10
                )
                st.plotly_chart(fig_category, use_container_width=True)

                # Show category details table
                if st.checkbox("Show category details", key="cat_details"):
                    cat_summary = df_expenses.groupby('category').agg({
                        'amount': ['sum', 'count', 'mean']
                    }).round(2)
                    cat_summary.columns = ['Total (₪)', 'Count', 'Avg (₪)']
                    cat_summary['Total (₪)'] = cat_summary['Total (₪)'].abs()
                    cat_summary['Avg (₪)'] = cat_summary['Avg (₪)'].abs()
                    cat_summary = cat_summary.sort_values('Total (₪)', ascending=False)
                    st.dataframe(cat_summary, use_container_width=True)

            with col2:
                st.subheader("Top Merchants")
                # Extract merchant from description (first word/phrase)
                df_expenses_copy = df_expenses.copy()
                df_expenses_copy['merchant'] = df_expenses_copy['description'].str[:30]

                fig_merchants = category_bar(
                    df_expenses_copy,
                    title="Top 15 Merchants by Spending",
                    value_col="amount",
                    label_col="merchant",
                    top_n=15,
                    horizontal=True
                )
                st.plotly_chart(fig_merchants, use_container_width=True)

            # Row 2: Spending by Day of Week + Summary Stats
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Spending by Day of Week")
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_spending = df_expenses.groupby('day_of_week')['amount'].sum().abs()
                day_spending = day_spending.reindex(day_order, fill_value=0)

                fig_dow = go.Figure(data=[go.Bar(
                    x=day_spending.index,
                    y=day_spending.values,
                    marker=dict(color=COLORS['purple']),
                    hovertemplate='%{x}<br>%{y:,.2f}₪<extra></extra>'
                )])

                fig_dow.update_layout(
                    title="Average Spending by Day",
                    xaxis_title="Day of Week",
                    yaxis_title="Total Spending (₪)",
                    height=400
                )
                st.plotly_chart(fig_dow, use_container_width=True)

            with col2:
                st.subheader("Summary Statistics")
                total_spent = df_expenses['amount'].sum()
                avg_transaction = df_expenses['amount'].mean()
                median_transaction = df_expenses['amount'].median()
                max_transaction = df_expenses['amount'].min()  # Most negative = highest expense

                st.metric("Total Spent", format_currency(abs(total_spent)))
                st.metric("Average Transaction", format_currency(abs(avg_transaction)))
                st.metric("Median Transaction", format_currency(abs(median_transaction)))
                st.metric("Largest Single Expense", format_currency(abs(max_transaction)))

                # Daily average
                num_days = (end_date - start_date).days + 1
                daily_avg = abs(total_spent) / num_days
                st.metric("Average Daily Spending", format_currency(daily_avg))

            # Calendar Heatmap
            st.markdown("---")
            st.subheader("📅 Daily Spending Calendar")

            # Year selector for heatmap
            col_year1, col_year2 = st.columns([1, 3])
            with col_year1:
                available_years = sorted(df_all['date'].dt.year.unique(), reverse=True)
                if available_years:
                    selected_year = st.selectbox(
                        "Select Year",
                        options=available_years,
                        index=0,
                        key="heatmap_year"
                    )
                else:
                    selected_year = date.today().year

            with col_year2:
                st.caption("Hover over cells to see daily spending. Darker colors indicate higher spending.")

            # Filter data for selected year
            df_year = df_expenses[df_expenses['date'].dt.year == selected_year].copy()

            if not df_year.empty:
                fig_heatmap = calendar_heatmap(
                    df_year,
                    date_col='date',
                    value_col='amount',
                    year=selected_year,
                    title=f"Daily Spending Heatmap - {selected_year}",
                    colorscale='Reds'
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

                # Quick stats for the year
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                with col_s1:
                    year_total = df_year['amount'].sum()
                    st.metric("Year Total", format_currency(abs(year_total)))
                with col_s2:
                    year_avg = df_year['amount'].mean()
                    st.metric("Avg Transaction", format_currency(abs(year_avg)))
                with col_s3:
                    days_with_spending = df_year['date'].dt.date.nunique()
                    st.metric("Days with Spending", f"{days_with_spending} days")
                with col_s4:
                    max_day = df_year.groupby(df_year['date'].dt.date)['amount'].sum().abs().max()
                    st.metric("Highest Day", format_currency(max_day))
            else:
                st.info(f"No spending data available for {selected_year}")

    # ============================================================================
    # TAB 2: TRENDS
    # ============================================================================
    with tab2:
        st.header("Spending Trends Over Time")

        if df_expenses.empty:
            st.info("No expenses found in the selected period.")
        else:
            # Monthly Spending Over Time
            st.subheader("Monthly Spending Trend")
            fig_monthly = monthly_trend(
                df_expenses,
                title="Total Spending by Month",
                date_col="date",
                amount_col="amount",
                months=12
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

            # Category Trends (Stacked Area)
            st.subheader("Category Trends Over Time")

            # Prepare data for stacked area chart
            df_expenses_copy = df_expenses.copy()
            df_expenses_copy['month'] = pd.to_datetime(df_expenses_copy['date']).dt.to_period('M')

            # Get top 5 categories
            top_categories = df_expenses.groupby('category')['amount'].sum().abs().nlargest(5).index.tolist()
            df_top_cat = df_expenses_copy[df_expenses_copy['category'].isin(top_categories)]

            # Group by month and category
            monthly_by_cat = df_top_cat.groupby(['month', 'category'])['amount'].sum().abs().reset_index()
            monthly_by_cat['month'] = monthly_by_cat['month'].astype(str)

            fig_cat_trend = px.area(
                monthly_by_cat,
                x='month',
                y='amount',
                color='category',
                title="Top 5 Categories Trend (Stacked)",
                labels={'amount': 'Spending (₪)', 'month': 'Month'}
            )
            fig_cat_trend.update_layout(height=400)
            st.plotly_chart(fig_cat_trend, use_container_width=True)

            # Month-over-Month Comparison
            st.subheader("Month-over-Month Comparison")

            df_expenses_copy = df_expenses.copy()
            df_expenses_copy['month'] = pd.to_datetime(df_expenses_copy['date']).dt.to_period('M')
            monthly_totals = df_expenses_copy.groupby('month')['amount'].sum().abs()

            if len(monthly_totals) >= 2:
                # Calculate MoM change
                mom_change = monthly_totals.pct_change() * 100

                fig_mom = go.Figure()
                fig_mom.add_trace(go.Bar(
                    x=[str(m) for m in monthly_totals.index],
                    y=monthly_totals.values,
                    name='Spending',
                    marker=dict(color=COLORS['primary']),
                    yaxis='y',
                    hovertemplate='%{x}<br>%{y:,.2f}₪<extra></extra>'
                ))

                fig_mom.add_trace(go.Scatter(
                    x=[str(m) for m in mom_change.index],
                    y=mom_change.values,
                    name='% Change',
                    mode='lines+markers',
                    line=dict(color=COLORS['danger'], width=2),
                    yaxis='y2',
                    hovertemplate='%{x}<br>%{y:.1f}%<extra></extra>'
                ))

                fig_mom.update_layout(
                    title='Monthly Spending with MoM % Change',
                    xaxis=dict(title='Month'),
                    yaxis=dict(title='Spending (₪)', side='left'),
                    yaxis2=dict(title='% Change', side='right', overlaying='y'),
                    height=400,
                    hovermode='x unified'
                )
                st.plotly_chart(fig_mom, use_container_width=True)
            else:
                st.info("Need at least 2 months of data for MoM comparison")

            # Year-over-Year (if we have data spanning multiple years)
            df_expenses_copy = df_expenses.copy()
            df_expenses_copy['year'] = pd.to_datetime(df_expenses_copy['date']).dt.year
            df_expenses_copy['month_num'] = pd.to_datetime(df_expenses_copy['date']).dt.month

            years = df_expenses_copy['year'].unique()
            if len(years) > 1:
                st.subheader("Year-over-Year Comparison")

                yearly_monthly = df_expenses_copy.groupby(['year', 'month_num'])['amount'].sum().abs().reset_index()

                fig_yoy = px.line(
                    yearly_monthly,
                    x='month_num',
                    y='amount',
                    color='year',
                    title='Year-over-Year Monthly Spending',
                    labels={'month_num': 'Month', 'amount': 'Spending (₪)'},
                    markers=True
                )
                fig_yoy.update_layout(height=400)
                st.plotly_chart(fig_yoy, use_container_width=True)

    # ============================================================================
    # TAB 3: BALANCE & PORTFOLIO
    # ============================================================================
    with tab3:
        st.header("Balance & Portfolio Analysis")

        # Portfolio Composition
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Portfolio Composition")

            # Get accounts with balances (cached for 5 minutes)
            accounts_list = safe_call_with_spinner(
                get_accounts_cached,
                spinner_text="Loading account balances...",
                error_message="Failed to load account data",
                default_return=[]
            )

            # Filter accounts with positive balance
            accounts_data = []
            for acc in accounts_list:
                if acc['latest_balance'] > 0:
                    accounts_data.append({
                        'balance': acc['latest_balance'],
                        'account_type': acc['account_type'] or 'Other',
                        'institution': acc['institution'],
                        'account_id': acc['id']
                    })

            df_accounts = pd.DataFrame(accounts_data)

            if not df_accounts.empty:
                fig_portfolio = balance_distribution(
                    df_accounts,
                    title="Balance by Account Type",
                    value_col="balance",
                    label_col="account_type"
                )
                st.plotly_chart(fig_portfolio, use_container_width=True)
            else:
                st.info("No balance data available")

        with col2:
            st.subheader("Balance by Institution")

            if not df_accounts.empty:
                fig_inst = balance_distribution(
                    df_accounts,
                    title="Balance by Institution",
                    value_col="balance",
                    label_col="institution"
                )
                st.plotly_chart(fig_inst, use_container_width=True)
            else:
                st.info("No balance data available")

        # Balance History
        st.subheader("Balance History Over Time")

        with st.spinner("Loading balance history..."):
            session = get_session()
            try:
                balance_history_query = session.query(
                    Balance.balance_date,
                    Balance.total_amount,
                    Account.institution
                ).join(
                    Account,
                    Account.id == Balance.account_id
                ).filter(
                    and_(
                        Balance.balance_date >= start_date,
                        Balance.balance_date <= end_date
                    )
                ).order_by(Balance.balance_date).all()
            finally:
                session.close()

        if balance_history_query:
            balance_data = []
            for balance_date, total_amount, institution in balance_history_query:
                balance_data.append({
                    'date': balance_date,
                    'balance': total_amount,
                    'institution': institution
                })

            df_balance_history = pd.DataFrame(balance_data)

            fig_balance_hist = balance_history(
                df_balance_history,
                title="Balance Over Time by Institution",
                x_col="date",
                y_col="balance",
                group_col="institution"
            )
            st.plotly_chart(fig_balance_hist, use_container_width=True)
        else:
            st.info("No balance history available for selected period")

        # Account Summary Table
        st.subheader("Account Summary")

        if not df_accounts.empty:
            with st.spinner("Calculating account summaries..."):
                summary_data = []
                session = get_session()
                try:
                    for _, row in df_accounts.iterrows():
                        acc_id = row['account_id']
                        # Get transaction count for this account from cached data
                        txn_count = len([t for t in transactions_list if t['account_id'] == acc_id])

                        summary_data.append({
                            'Type': row['account_type'],
                            'Institution': row['institution'],
                            'Balance': format_currency(row['balance']),
                            'Transactions': txn_count
                        })
                finally:
                    session.close()

                df_summary = pd.DataFrame(summary_data)
                st.dataframe(df_summary, use_container_width=True, hide_index=True)

    # ============================================================================
    # TAB 4: TAGS ANALYSIS
    # ============================================================================
    with tab4:
        st.header("Tags Analysis")

        # Get all tags with transaction data
        with st.spinner("Loading tag data..."):
            session = get_session()
            try:
                tags_query = session.query(
                    Tag.name,
                    func.count(TransactionTag.transaction_id).label('count'),
                    func.sum(Transaction.original_amount).label('total_amount')
                ).join(
                    TransactionTag,
                    TransactionTag.tag_id == Tag.id
                ).join(
                    Transaction,
                    Transaction.id == TransactionTag.transaction_id
                ).filter(
                    and_(
                        Transaction.transaction_date >= start_date,
                        Transaction.transaction_date <= end_date,
                        Transaction.original_amount < 0  # Only expenses
                    )
                ).group_by(Tag.name).all()
            finally:
                session.close()

        if tags_query and len(tags_query) > 0:
            # Spending by Tag
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Spending by Tag")

                tags_data = []
                for tag_name, count, total in tags_query:
                    tags_data.append({
                        'tag': tag_name,
                        'count': count,
                        'amount': abs(total) if total else 0
                    })

                df_tags = pd.DataFrame(tags_data)

                fig_tags = category_bar(
                    df_tags,
                    title="Top Tags by Spending",
                    value_col="amount",
                    label_col="tag",
                    top_n=15,
                    horizontal=True
                )
                st.plotly_chart(fig_tags, use_container_width=True)

            with col2:
                st.subheader("Tag Distribution")

                # Treemap for tag distribution
                fig_treemap = px.treemap(
                    df_tags,
                    path=['tag'],
                    values='amount',
                    title='Tag Distribution (Treemap)',
                    color='amount',
                    color_continuous_scale='Blues'
                )
                fig_treemap.update_layout(height=400)
                st.plotly_chart(fig_treemap, use_container_width=True)

            # Tag Trends Over Time
            st.subheader("Tag Trends Over Time")

            # Get top 5 tags
            top_tags = df_tags.nlargest(5, 'amount')['tag'].tolist()

            # Get transaction data for these tags
            with st.spinner("Loading tag trends..."):
                session = get_session()
                try:
                    tag_trend_query = session.query(
                        Tag.name,
                        Transaction.transaction_date,
                        Transaction.original_amount
                    ).join(
                        TransactionTag,
                        TransactionTag.tag_id == Tag.id
                    ).join(
                        Transaction,
                        Transaction.id == TransactionTag.transaction_id
                    ).filter(
                        and_(
                            Tag.name.in_(top_tags),
                            Transaction.transaction_date >= start_date,
                            Transaction.transaction_date <= end_date,
                            Transaction.original_amount < 0
                        )
                    ).all()
                finally:
                    session.close()

            if tag_trend_query:
                tag_trend_data = []
                for tag_name, txn_date, amount in tag_trend_query:
                    tag_trend_data.append({
                        'tag': tag_name,
                        'date': txn_date,
                        'amount': abs(amount)
                    })

                df_tag_trend = pd.DataFrame(tag_trend_data)
                df_tag_trend['month'] = pd.to_datetime(df_tag_trend['date']).dt.to_period('M')
                monthly_tag = df_tag_trend.groupby(['month', 'tag'])['amount'].sum().reset_index()
                monthly_tag['month'] = monthly_tag['month'].astype(str)

                fig_tag_trend = px.line(
                    monthly_tag,
                    x='month',
                    y='amount',
                    color='tag',
                    title='Top 5 Tags Trend Over Time',
                    labels={'amount': 'Spending (₪)', 'month': 'Month'},
                    markers=True
                )
                fig_tag_trend.update_layout(height=400)
                st.plotly_chart(fig_tag_trend, use_container_width=True)

            # Tag summary table
            st.subheader("Tag Summary")
            df_tags_display = df_tags.copy()
            df_tags_display['Amount'] = df_tags_display['amount'].apply(format_currency)
            df_tags_display['Count'] = df_tags_display['count']
            df_tags_display['Avg per Transaction'] = (df_tags_display['amount'] / df_tags_display['count']).apply(format_currency)
            st.dataframe(
                df_tags_display[['tag', 'Count', 'Amount', 'Avg per Transaction']].rename(columns={'tag': 'Tag'}),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No tagged transactions found in the selected period. Go to the **Tags** page to start tagging your transactions!")

        # Untagged transactions summary
        st.subheader("Untagged Transactions")

        with st.spinner("Calculating untagged transactions..."):
            session = get_session()
            try:
                untagged_count = session.query(func.count(Transaction.id)).filter(
                    and_(
                        Transaction.transaction_date >= start_date,
                        Transaction.transaction_date <= end_date,
                        Transaction.original_amount < 0,
                        ~Transaction.id.in_(
                            session.query(TransactionTag.transaction_id)
                        )
                    )
                ).scalar()

                untagged_amount = session.query(func.sum(Transaction.original_amount)).filter(
                    and_(
                        Transaction.transaction_date >= start_date,
                        Transaction.transaction_date <= end_date,
                        Transaction.original_amount < 0,
                        ~Transaction.id.in_(
                            session.query(TransactionTag.transaction_id)
                        )
                    )
                ).scalar() or 0
            finally:
                session.close()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Untagged Transactions", format_number(untagged_count))
        with col2:
            st.metric("Untagged Amount", format_currency(abs(untagged_amount)))

        if untagged_count > 0:
            st.info(f"💡 You have {untagged_count} untagged expenses. Consider tagging them for better insights!")

    # ============================================================================
    # TAB 5: COMPARISONS
    # ============================================================================
    with tab5:
        st.header("Detailed Comparisons")

        # Month vs Month Comparison
        st.subheader("Month vs Month Comparison")

        # Get available months
        df_all_copy = df_all.copy()
        df_all_copy['month'] = pd.to_datetime(df_all_copy['date']).dt.to_period('M')
        available_months = sorted(df_all_copy['month'].unique(), reverse=True)

        # Add month column to df_expenses for filtering
        df_expenses_with_month = df_expenses.copy()
        df_expenses_with_month['month'] = pd.to_datetime(df_expenses_with_month['date']).dt.to_period('M')

        if len(available_months) >= 2:
            col1, col2 = st.columns(2)

            with col1:
                month1 = st.selectbox(
                    "Select first month",
                    options=[str(m) for m in available_months],
                    key="month1"
                )

            with col2:
                month2 = st.selectbox(
                    "Select second month",
                    options=[str(m) for m in available_months],
                    index=1 if len(available_months) > 1 else 0,
                    key="month2"
                )

            if month1 and month2 and month1 != month2:
                df_month1 = df_expenses_with_month[df_expenses_with_month['month'] == pd.Period(month1)]
                df_month2 = df_expenses_with_month[df_expenses_with_month['month'] == pd.Period(month2)]

                # Side by side metrics
                col1, col2, col3 = st.columns(3)

                total1 = abs(df_month1['amount'].sum())
                total2 = abs(df_month2['amount'].sum())
                diff = total1 - total2
                pct_change = ((total1 - total2) / total2 * 100) if total2 > 0 else 0

                with col1:
                    st.metric(f"{month1}", format_currency(total1))

                with col2:
                    st.metric(f"{month2}", format_currency(total2))

                with col3:
                    st.metric("Difference", format_currency(diff), f"{pct_change:+.1f}%")

                # Category comparison
                cat1 = df_month1.groupby('category')['amount'].sum().abs()
                cat2 = df_month2.groupby('category')['amount'].sum().abs()

                comparison_df = pd.DataFrame({
                    month1: cat1,
                    month2: cat2
                }).fillna(0).sort_values(month1, ascending=False).head(10)

                fig_comparison = go.Figure()
                fig_comparison.add_trace(go.Bar(
                    name=month1,
                    x=comparison_df.index,
                    y=comparison_df[month1],
                    marker=dict(color=COLORS['primary'])
                ))
                fig_comparison.add_trace(go.Bar(
                    name=month2,
                    x=comparison_df.index,
                    y=comparison_df[month2],
                    marker=dict(color=COLORS['success'])
                ))

                fig_comparison.update_layout(
                    title='Category Comparison',
                    xaxis_title='Category',
                    yaxis_title='Spending (₪)',
                    barmode='group',
                    height=400
                )
                st.plotly_chart(fig_comparison, use_container_width=True)
        else:
            st.info("Need at least 2 months of data for comparison")

        st.markdown("---")

        # Category Deep Dive
        st.subheader("Category Deep Dive")

        if not df_expenses.empty:
            categories = sorted(df_expenses['category'].unique())
            selected_category = st.selectbox(
                "Select category to analyze",
                options=categories,
                key="category_deepdive"
            )

            if selected_category:
                df_cat = df_expenses[df_expenses['category'] == selected_category]

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Spent", format_currency(abs(df_cat['amount'].sum())))

                with col2:
                    st.metric("Transactions", format_number(len(df_cat)))

                with col3:
                    st.metric("Average", format_currency(abs(df_cat['amount'].mean())))

                # Monthly trend for this category
                df_cat_copy = df_cat.copy()
                df_cat_copy['month'] = pd.to_datetime(df_cat_copy['date']).dt.to_period('M')
                monthly_cat = df_cat_copy.groupby('month')['amount'].sum().abs()

                fig_cat_trend = go.Figure(data=[go.Bar(
                    x=[str(m) for m in monthly_cat.index],
                    y=monthly_cat.values,
                    marker=dict(color=COLORS['warning']),
                    hovertemplate='%{x}<br>%{y:,.2f}₪<extra></extra>'
                )])

                fig_cat_trend.update_layout(
                    title=f'{selected_category} - Monthly Trend',
                    xaxis_title='Month',
                    yaxis_title='Spending (₪)',
                    height=350
                )
                st.plotly_chart(fig_cat_trend, use_container_width=True)

                # Top transactions in this category
                st.markdown("**Top 10 Transactions**")
                df_cat_top = df_cat.nsmallest(10, 'amount')[['date', 'description', 'amount']]
                df_cat_top['amount'] = df_cat_top['amount'].apply(format_currency)
                df_cat_top['date'] = df_cat_top['date'].apply(lambda d: d.strftime('%Y-%m-%d'))
                st.dataframe(
                    df_cat_top.rename(columns={'date': 'Date', 'description': 'Description', 'amount': 'Amount'}),
                    use_container_width=True,
                    hide_index=True
                )

        st.markdown("---")

        # Account Comparison
        st.subheader("Account Comparison")

        # Get accounts with transactions in period
        account_spending = df_expenses.groupby('account_id')['amount'].sum().abs().sort_values(ascending=False)

        if len(account_spending) > 0:
            # Get account names from cached data
            accounts_cached = safe_call_with_spinner(
                get_accounts_cached,
                spinner_text="Loading account details...",
                error_message="Failed to load accounts",
                default_return=[]
            )
            account_names = {}
            for acc in accounts_cached:
                account_names[acc['id']] = f"{acc['institution']} - {acc['account_type'] or 'Account'}"

            # Create comparison chart
            fig_acc_comp = go.Figure(data=[go.Bar(
                x=[account_names.get(acc_id, f"Account {acc_id}") for acc_id in account_spending.index],
                y=account_spending.values,
                marker=dict(color=COLORS['info']),
                hovertemplate='%{x}<br>%{y:,.2f}₪<extra></extra>'
            )])

            fig_acc_comp.update_layout(
                title='Spending by Account',
                xaxis_title='Account',
                yaxis_title='Total Spending (₪)',
                height=400
            )
            st.plotly_chart(fig_acc_comp, use_container_width=True)

    st.markdown("---")

    # Export Options
    st.subheader("📥 Export Data")

    col1, col2 = st.columns(2)

    with col1:
        # Export to CSV
        if st.button("Export Transactions to CSV", use_container_width=True):
            csv = df_all.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"transactions_{start_date}_{end_date}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col2:
        # Export summary
        if st.button("Export Summary to CSV", use_container_width=True):
            summary = df_expenses.groupby('category').agg({
                'amount': ['sum', 'count', 'mean']
            }).round(2)
            summary.columns = ['Total', 'Count', 'Average']
            csv_summary = summary.to_csv()
            st.download_button(
                label="Download Summary CSV",
                data=csv_summary,
                file_name=f"summary_{start_date}_{end_date}.csv",
                mime="text/csv",
                use_container_width=True
            )
