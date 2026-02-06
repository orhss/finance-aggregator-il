"""
Analytics & Reports Page - Comprehensive financial insights

Boilerplate (page config, auth, theme, sidebar) is handled by main.py.
This file contains only the page-specific content.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, date
from typing import Optional

from streamlit_app.utils.session import format_amount_private, get_accounts_display
from streamlit_app.utils.formatters import format_number, format_datetime
from streamlit_app.utils.cache import (
    get_transactions_cached,
    get_category_spending_cached,
    get_monthly_trend_cached,
    get_tags_cached
)
from streamlit_app.utils.errors import safe_call_with_spinner, ErrorBoundary
from streamlit_app.components.empty_states import empty_analytics_state
from streamlit_app.components.loading import contextual_spinner
from streamlit_app.components.charts import (
    spending_donut,
    category_bar,
    balance_history,
    balance_distribution,
    monthly_trend,
    COLORS,
    CATEGORY_COLORS
)
from streamlit_app.components.heatmap import calendar_heatmap
from streamlit_app.components.theme import render_page_header
from streamlit_app.components.cards import render_metric_row
from streamlit_app.components.filters import date_range_picker
from streamlit_app.utils.mobile import is_mobile
from streamlit_app.components.mobile_ui import apply_mobile_css, summary_card, bottom_navigation

from streamlit_app.utils.analytics_helpers import (
    get_period_options,
    transactions_to_dataframe,
    calculate_spending_metrics,
    get_spending_by_day_of_week,
)


def render_mobile_analytics():
    """Render simplified mobile analytics view."""
    # Apply mobile CSS
    apply_mobile_css()

    render_page_header("Analytics")

    # Period selector - use shared helper
    today = date.today()
    period_options = get_period_options(today)
    # Mobile only shows subset of options
    mobile_options = ["This Month", "Last Month", "Last 3 Months"]

    selected_period = st.selectbox(
        "Period",
        options=mobile_options,
        index=0,
        key="mobile_analytics_period",
        label_visibility="collapsed"
    )

    start_date, end_date = period_options[selected_period]

    # Get category spending data
    try:
        df_spending = get_category_spending_cached(start_date, end_date, top_n=5)

        if not df_spending.empty:
            total_spent = df_spending['amount'].sum()

            # Summary card for total spending
            summary_card(
                title=f"Total Spent ({selected_period})",
                value=format_amount_private(total_spent),
            )

            st.markdown("")  # Spacing

            # Top categories as horizontal bar chart
            st.markdown("**Top Categories**")

            fig = px.bar(
                df_spending.head(5),
                x='amount',
                y='category',
                orientation='h',
                color='category',
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(
                showlegend=False,
                height=250,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="",
                yaxis_title="",
                yaxis={'categoryorder': 'total ascending'},
            )
            fig.update_traces(
                texttemplate='%{x:,.0f}',
                textposition='outside'
            )
            st.plotly_chart(fig, width="stretch")

        else:
            st.info("No spending data for this period")

    except Exception as e:
        st.warning(f"Could not load category data: {str(e)}")

    st.markdown("")  # Spacing

    # Monthly trend (last 6 months)
    st.markdown("**Monthly Trend**")

    try:
        df_trend = get_monthly_trend_cached(months_back=6)

        if not df_trend.empty:
            fig = px.line(
                df_trend,
                x='month_name',
                y='amount',
                markers=True,
            )
            fig.update_layout(
                showlegend=False,
                height=200,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="",
                yaxis_title="",
            )
            fig.update_traces(
                line_color='#667eea',
                marker_color='#667eea',
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No trend data available")

    except Exception as e:
        st.warning(f"Could not load trend data: {str(e)}")

    # Bottom navigation
    bottom_navigation(current="analytics")


def render_desktop_analytics():
    """Render full desktop analytics view."""
    # Page header
    render_page_header("Analytics")

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

        # Time range selector - use unified component
        start_date, end_date = date_range_picker(
            key_prefix="analytics",
            mode="dropdown",
            show_custom=True,
            default_option="Last 3 Months"
        )
        st.info(f"Showing data from **{start_date}** to **{end_date}**")

        # Fetch transactions for selected period (cached for 5 minutes)
        transactions_list = safe_call_with_spinner(
            get_transactions_cached,
            spinner_text=contextual_spinner("analyzing", "transaction patterns"),
            error_message="Failed to load transaction data",
            default_return=[],
            start_date=start_date,
            end_date=end_date
        )

        # Convert to DataFrame using shared helper
        df_all = transactions_to_dataframe(transactions_list)

        if df_all.empty:
            st.warning("No transactions found in the selected date range.")
            st.stop()

        # Convert date column to datetime for proper .dt accessor usage
        df_all['date'] = pd.to_datetime(df_all['date'])

        # Filter for expenses only (for most charts)
        df_expenses = df_all[df_all['is_expense']].copy()
        # Ensure date column is datetime in df_expenses as well
        df_expenses['date'] = pd.to_datetime(df_expenses['date'])

        # Summary metrics row - use shared helper
        metrics = calculate_spending_metrics(df_expenses)

        render_metric_row([
            {"value": format_amount_private(metrics['total_spending']), "label": "Total Spending"},
            {"value": f"{len(df_all):,}", "label": "Transactions"},
            {"value": metrics['top_category'], "label": "Top Category"},
            {"value": format_amount_private(metrics['avg_transaction']), "label": "Avg Transaction"},
        ])

        st.markdown("")  # Spacing

        # Create tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Spending Analysis",
            "Trends",
            "Balance & Portfolio",
            "Tags Analysis",
            "Comparisons"
        ])

        # ============================================================================
        # TAB 1: SPENDING ANALYSIS
        # ============================================================================
        with tab1:
            st.markdown('<div class="section-title" style="font-size: 1.25rem;">Spending Analysis</div>', unsafe_allow_html=True)

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
                    st.plotly_chart(fig_category, width="stretch")

                    # Show category details table
                    if st.checkbox("Show category details", key="cat_details"):
                        cat_summary = df_expenses.groupby('category').agg({
                            'amount': ['sum', 'count', 'mean']
                        }).round(2)
                        cat_summary.columns = ['Total', 'Count', 'Avg']
                        cat_summary['Total'] = cat_summary['Total'].abs()
                        cat_summary['Avg'] = cat_summary['Avg'].abs()
                        cat_summary = cat_summary.sort_values('Total', ascending=False)
                        st.dataframe(cat_summary, width="stretch")

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
                    st.plotly_chart(fig_merchants, width="stretch")

                # Row 2: Spending by Day of Week + Summary Stats
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Spending by Day of Week")
                    # Use shared helper for day of week spending
                    day_spending = get_spending_by_day_of_week(df_expenses)

                    fig_dow = go.Figure(data=[go.Bar(
                        x=day_spending.index,
                        y=day_spending.values,
                        marker=dict(color=COLORS['purple']),
                        hovertemplate='%{x}<br>%{y:,.2f}<extra></extra>'
                    )])

                    fig_dow.update_layout(
                        title="Average Spending by Day",
                        xaxis_title="Day of Week",
                        yaxis_title="Total Spending",
                        height=400
                    )
                    st.plotly_chart(fig_dow, width="stretch")

                with col2:
                    st.markdown('<div class="section-title">Summary Statistics</div>', unsafe_allow_html=True)
                    total_spent = df_expenses['amount'].sum()
                    avg_transaction = df_expenses['amount'].mean()
                    median_transaction = df_expenses['amount'].median()
                    max_transaction = df_expenses['amount'].min()  # Most negative = highest expense

                    # Daily average
                    num_days = (end_date - start_date).days + 1
                    daily_avg = abs(total_spent) / num_days

                    # Render as styled stat cards in a grid
                    st.markdown(f'''
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;">
                        <div class="stat-card">
                            <div class="stat-label">Total Spent</div>
                            <div class="stat-value negative">{format_amount_private(abs(total_spent))}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Avg Transaction</div>
                            <div class="stat-value">{format_amount_private(abs(avg_transaction))}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Median</div>
                            <div class="stat-value">{format_amount_private(abs(median_transaction))}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Largest Expense</div>
                            <div class="stat-value negative">{format_amount_private(abs(max_transaction))}</div>
                        </div>
                        <div class="stat-card" style="grid-column: span 2;">
                            <div class="stat-label">Daily Average</div>
                            <div class="stat-value">{format_amount_private(daily_avg)}</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)

                # Calendar Heatmap
                st.markdown("")  # Spacing
                st.subheader("Daily Spending Calendar")

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
                    st.plotly_chart(fig_heatmap, width="stretch")

                    # Quick stats for the year
                    year_total = df_year['amount'].sum()
                    year_avg = df_year['amount'].mean()
                    days_with_spending = df_year['date'].dt.date.nunique()
                    max_day = df_year.groupby(df_year['date'].dt.date)['amount'].sum().abs().max()

                    render_metric_row([
                        {"value": format_amount_private(abs(year_total)), "label": "Year Total"},
                        {"value": format_amount_private(abs(year_avg)), "label": "Avg Transaction"},
                        {"value": f"{days_with_spending} days", "label": "Days with Spending"},
                        {"value": format_amount_private(max_day), "label": "Highest Day"},
                    ])
                else:
                    st.info(f"No spending data available for {selected_year}")

        # ============================================================================
        # TAB 2: TRENDS
        # ============================================================================
        with tab2:
            st.markdown('<div class="section-title" style="font-size: 1.25rem;">Spending Trends Over Time</div>', unsafe_allow_html=True)

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
                st.plotly_chart(fig_monthly, width="stretch")

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
                    labels={'amount': 'Spending', 'month': 'Month'}
                )
                fig_cat_trend.update_layout(height=400)
                st.plotly_chart(fig_cat_trend, width="stretch")

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
                        hovertemplate='%{x}<br>%{y:,.2f}<extra></extra>'
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
                        yaxis=dict(title='Spending', side='left'),
                        yaxis2=dict(title='% Change', side='right', overlaying='y'),
                        height=400,
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_mom, width="stretch")
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
                        labels={'month_num': 'Month', 'amount': 'Spending'},
                        markers=True
                    )
                    fig_yoy.update_layout(height=400)
                    st.plotly_chart(fig_yoy, width="stretch")

        # ============================================================================
        # TAB 3: BALANCE & PORTFOLIO
        # ============================================================================
        with tab3:
            st.markdown('<div class="section-title" style="font-size: 1.25rem;">Balance & Portfolio Analysis</div>', unsafe_allow_html=True)

            # Portfolio Composition
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Portfolio Composition")

                # Get accounts with balances (cached for 5 minutes)
                accounts_list = safe_call_with_spinner(
                    get_accounts_display,
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
                    st.plotly_chart(fig_portfolio, width="stretch")
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
                    st.plotly_chart(fig_inst, width="stretch")
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
                st.plotly_chart(fig_balance_hist, width="stretch")
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
                                'Balance': format_amount_private(row['balance']),
                                'Transactions': txn_count
                            })
                    finally:
                        session.close()

                    df_summary = pd.DataFrame(summary_data)
                    st.dataframe(df_summary, width="stretch", hide_index=True)

        # ============================================================================
        # TAB 4: TAGS ANALYSIS
        # ============================================================================
        with tab4:
            st.markdown('<div class="section-title" style="font-size: 1.25rem;">Tags Analysis</div>', unsafe_allow_html=True)

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
                    st.plotly_chart(fig_tags, width="stretch")

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
                    st.plotly_chart(fig_treemap, width="stretch")

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
                        labels={'amount': 'Spending', 'month': 'Month'},
                        markers=True
                    )
                    fig_tag_trend.update_layout(height=400)
                    st.plotly_chart(fig_tag_trend, width="stretch")

                # Tag summary table
                st.subheader("Tag Summary")
                df_tags_display = df_tags.copy()
                df_tags_display['Amount'] = df_tags_display['amount'].apply(format_amount_private)
                df_tags_display['Count'] = df_tags_display['count']
                df_tags_display['Avg per Transaction'] = (df_tags_display['amount'] / df_tags_display['count']).apply(format_amount_private)
                st.dataframe(
                    df_tags_display[['tag', 'Count', 'Amount', 'Avg per Transaction']].rename(columns={'tag': 'Tag'}),
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info("No tagged transactions found in the selected period. Go to the **Organize** page to start tagging your transactions!")

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

            render_metric_row([
                {"value": format_number(untagged_count), "label": "Untagged Transactions"},
                {"value": format_amount_private(abs(untagged_amount)), "label": "Untagged Amount"},
            ])

            if untagged_count > 0:
                st.info(f"You have {untagged_count} untagged expenses. Consider tagging them for better insights!")

        # ============================================================================
        # TAB 5: COMPARISONS
        # ============================================================================
        with tab5:
            st.markdown('<div class="section-title" style="font-size: 1.25rem;">Detailed Comparisons</div>', unsafe_allow_html=True)

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
                    total1 = abs(df_month1['amount'].sum())
                    total2 = abs(df_month2['amount'].sum())
                    diff = total1 - total2
                    pct_change = ((total1 - total2) / total2 * 100) if total2 > 0 else 0
                    diff_class = "positive" if diff > 0 else "negative" if diff < 0 else ""

                    st.markdown(f'''
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem;">
                        <div class="stat-card">
                            <div class="stat-label">{month1}</div>
                            <div class="stat-value">{format_amount_private(total1)}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">{month2}</div>
                            <div class="stat-value">{format_amount_private(total2)}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Difference</div>
                            <div class="stat-value {diff_class}">{format_amount_private(diff)}</div>
                            <div class="metric-sublabel">{pct_change:+.1f}%</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)

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
                        yaxis_title='Spending',
                        barmode='group',
                        height=400
                    )
                    st.plotly_chart(fig_comparison, width="stretch")
            else:
                st.info("Need at least 2 months of data for comparison")

            st.markdown("")  # Spacing

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

                    render_metric_row([
                        {"value": format_amount_private(abs(df_cat['amount'].sum())), "label": "Total Spent"},
                        {"value": format_number(len(df_cat)), "label": "Transactions"},
                        {"value": format_amount_private(abs(df_cat['amount'].mean())), "label": "Average"},
                    ])

                    # Monthly trend for this category
                    df_cat_copy = df_cat.copy()
                    df_cat_copy['month'] = pd.to_datetime(df_cat_copy['date']).dt.to_period('M')
                    monthly_cat = df_cat_copy.groupby('month')['amount'].sum().abs()

                    fig_cat_trend = go.Figure(data=[go.Bar(
                        x=[str(m) for m in monthly_cat.index],
                        y=monthly_cat.values,
                        marker=dict(color=COLORS['warning']),
                        hovertemplate='%{x}<br>%{y:,.2f}<extra></extra>'
                    )])

                    fig_cat_trend.update_layout(
                        title=f'{selected_category} - Monthly Trend',
                        xaxis_title='Month',
                        yaxis_title='Spending',
                        height=350
                    )
                    st.plotly_chart(fig_cat_trend, width="stretch")

                    # Top transactions in this category
                    st.markdown("**Top 10 Transactions**")
                    df_cat_top = df_cat.nsmallest(10, 'amount')[['date', 'description', 'amount']]
                    df_cat_top['amount'] = df_cat_top['amount'].apply(format_amount_private)
                    df_cat_top['date'] = df_cat_top['date'].apply(lambda d: d.strftime('%Y-%m-%d'))
                    st.dataframe(
                        df_cat_top.rename(columns={'date': 'Date', 'description': 'Description', 'amount': 'Amount'}),
                        width="stretch",
                        hide_index=True
                    )

            st.markdown("")  # Spacing

            # Account Comparison
            st.subheader("Account Comparison")

            # Get accounts with transactions in period
            account_spending = df_expenses.groupby('account_id')['amount'].sum().abs().sort_values(ascending=False)

            if len(account_spending) > 0:
                # Get account names from cached data
                accounts_cached = safe_call_with_spinner(
                    get_accounts_display,
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
                    hovertemplate='%{x}<br>%{y:,.2f}<extra></extra>'
                )])

                fig_acc_comp.update_layout(
                    title='Spending by Account',
                    xaxis_title='Account',
                    yaxis_title='Total Spending',
                    height=400
                )
                st.plotly_chart(fig_acc_comp, width="stretch")

        st.markdown("")  # Spacing

        # Export Options
        st.subheader("Export Data")

        col1, col2 = st.columns(2)

        with col1:
            # Export to CSV
            if st.button("Export Transactions to CSV", width="stretch"):
                csv = df_all.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"transactions_{start_date}_{end_date}.csv",
                    mime="text/csv",
                    width="stretch"
                )

        with col2:
            # Export summary
            if st.button("Export Summary to CSV", width="stretch"):
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
                    width="stretch"
                )


# Main routing based on device type
if is_mobile():
    render_mobile_analytics()
else:
    render_desktop_analytics()
