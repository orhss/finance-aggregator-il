"""
Reusable chart components using Plotly
Provides consistent chart styling and functionality across the application
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List, Dict
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.formatters import format_currency


# Color palette for charts
COLORS = {
    'primary': '#1976d2',      # Material Blue 700
    'success': '#00897b',      # Material Teal 600 (income)
    'danger': '#c62828',       # Material Red 800 (expense)
    'warning': '#f57c00',      # Material Orange 700
    'info': '#0097a7',         # Material Cyan 700
    'purple': '#7b1fa2',       # Material Purple 700
    'gray': '#757575',         # Material Gray 600
    # Transparent versions for fills
    'primary_light': 'rgba(25, 118, 210, 0.1)',
    'success_light': 'rgba(0, 137, 123, 0.1)',
    'danger_light': 'rgba(198, 40, 40, 0.1)',
    'warning_light': 'rgba(245, 124, 0, 0.1)',
    'info_light': 'rgba(0, 151, 167, 0.1)',
}

CATEGORY_COLORS = px.colors.qualitative.Set3


def spending_donut(
    data: pd.DataFrame,
    title: str = "Spending by Category",
    value_col: str = "amount",
    label_col: str = "category",
    top_n: int = 10
) -> go.Figure:
    """
    Create donut chart for spending breakdown

    Args:
        data: DataFrame with spending data
        title: Chart title
        value_col: Column name for values
        label_col: Column name for labels
        top_n: Number of top categories to show

    Returns:
        Plotly figure object
    """
    if data.empty:
        return _empty_chart(title)

    # Aggregate by category and get top N
    grouped = data.groupby(label_col)[value_col].sum().abs().sort_values(ascending=False)
    top_categories = grouped.head(top_n)

    # Create donut chart
    fig = go.Figure(data=[go.Pie(
        labels=top_categories.index,
        values=top_categories.values,
        hole=0.4,
        marker=dict(colors=CATEGORY_COLORS),
        textinfo='label+percent',
        textposition='outside',
        hovertemplate='<b>%{label}</b><br>%{value:,.2f}₪<br>%{percent}<extra></extra>'
    )])

    fig.update_layout(
        title=title,
        showlegend=True,
        height=400,
        margin=dict(t=50, b=20, l=20, r=20)
    )

    return fig


def trend_line(
    data: pd.DataFrame,
    title: str = "Spending Trend",
    x_col: str = "date",
    y_col: str = "amount",
    group_col: Optional[str] = None
) -> go.Figure:
    """
    Create line chart for trends over time

    Args:
        data: DataFrame with time series data
        title: Chart title
        x_col: Column name for x-axis (dates)
        y_col: Column name for y-axis (values)
        group_col: Optional column for grouping (multiple lines)

    Returns:
        Plotly figure object
    """
    if data.empty:
        return _empty_chart(title)

    if group_col and group_col in data.columns:
        # Multiple lines
        fig = px.line(
            data,
            x=x_col,
            y=y_col,
            color=group_col,
            title=title,
            markers=True
        )
    else:
        # Single line
        fig = go.Figure(data=[go.Scatter(
            x=data[x_col],
            y=data[y_col].abs(),
            mode='lines+markers',
            line=dict(color=COLORS['primary'], width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor=COLORS['primary_light'],
            hovertemplate='%{x}<br>%{y:,.2f}₪<extra></extra>'
        )])

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Amount (₪)",
        hovermode='x unified',
        height=400,
        margin=dict(t=50, b=50, l=50, r=20)
    )

    return fig


def category_bar(
    data: pd.DataFrame,
    title: str = "Top Categories",
    value_col: str = "amount",
    label_col: str = "category",
    top_n: int = 15,
    horizontal: bool = True
) -> go.Figure:
    """
    Create bar chart for category comparison

    Args:
        data: DataFrame with category data
        title: Chart title
        value_col: Column name for values
        label_col: Column name for labels
        top_n: Number of top categories to show
        horizontal: If True, horizontal bars

    Returns:
        Plotly figure object
    """
    if data.empty:
        return _empty_chart(title)

    # Aggregate and get top N
    grouped = data.groupby(label_col)[value_col].sum().abs().sort_values(ascending=True)
    top_categories = grouped.tail(top_n)

    if horizontal:
        fig = go.Figure(data=[go.Bar(
            y=top_categories.index,
            x=top_categories.values,
            orientation='h',
            marker=dict(color=COLORS['primary']),
            hovertemplate='<b>%{y}</b><br>%{x:,.2f}₪<extra></extra>'
        )])
    else:
        fig = go.Figure(data=[go.Bar(
            x=top_categories.index,
            y=top_categories.values,
            marker=dict(color=COLORS['primary']),
            hovertemplate='<b>%{x}</b><br>%{y:,.2f}₪<extra></extra>'
        )])

    fig.update_layout(
        title=title,
        xaxis_title="Amount (₪)" if horizontal else "Category",
        yaxis_title="Category" if horizontal else "Amount (₪)",
        height=max(400, top_n * 25) if horizontal else 400,
        margin=dict(t=50, b=50, l=150 if horizontal else 50, r=20),
        showlegend=False
    )

    return fig


def balance_history(
    data: pd.DataFrame,
    title: str = "Balance History",
    x_col: str = "date",
    y_col: str = "balance",
    group_col: Optional[str] = None
) -> go.Figure:
    """
    Create line chart for balance over time

    Args:
        data: DataFrame with balance history
        title: Chart title
        x_col: Column name for dates
        y_col: Column name for balance values
        group_col: Optional column for grouping (multiple accounts)

    Returns:
        Plotly figure object
    """
    if data.empty:
        return _empty_chart(title)

    if group_col and group_col in data.columns:
        # Multiple lines for different accounts
        fig = px.line(
            data,
            x=x_col,
            y=y_col,
            color=group_col,
            title=title,
            markers=True
        )
    else:
        # Single line
        fig = go.Figure(data=[go.Scatter(
            x=data[x_col],
            y=data[y_col],
            mode='lines+markers',
            line=dict(color=COLORS['success'], width=2),
            marker=dict(size=6),
            hovertemplate='%{x}<br>Balance: %{y:,.2f}₪<extra></extra>'
        )])

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Balance (₪)",
        hovermode='x unified',
        height=400,
        margin=dict(t=50, b=50, l=50, r=20)
    )

    return fig


def spending_by_day(
    data: pd.DataFrame,
    title: str = "Daily Spending",
    date_col: str = "date",
    amount_col: str = "amount",
    days: int = 14
) -> go.Figure:
    """
    Create bar chart for daily spending (last N days)

    Args:
        data: DataFrame with transactions
        title: Chart title
        date_col: Column name for dates
        amount_col: Column name for amounts
        days: Number of recent days to show

    Returns:
        Plotly figure object
    """
    if data.empty:
        return _empty_chart(title)

    # Group by date and sum amounts
    daily = data.groupby(date_col)[amount_col].sum().abs()
    recent = daily.tail(days)

    fig = go.Figure(data=[go.Bar(
        x=recent.index,
        y=recent.values,
        marker=dict(color=COLORS['info']),
        hovertemplate='%{x}<br>%{y:,.2f}₪<extra></extra>'
    )])

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Spending (₪)",
        height=350,
        margin=dict(t=50, b=50, l=50, r=20),
        showlegend=False
    )

    return fig


def balance_distribution(
    data: pd.DataFrame,
    title: str = "Balance Distribution",
    value_col: str = "balance",
    label_col: str = "account_type"
) -> go.Figure:
    """
    Create pie chart for balance distribution by account type

    Args:
        data: DataFrame with account balances
        title: Chart title
        value_col: Column name for balance values
        label_col: Column name for account types

    Returns:
        Plotly figure object
    """
    if data.empty:
        return _empty_chart(title)

    # Group by account type
    grouped = data.groupby(label_col)[value_col].sum()

    fig = go.Figure(data=[go.Pie(
        labels=grouped.index,
        values=grouped.values,
        marker=dict(colors=CATEGORY_COLORS),
        textinfo='label+percent+value',
        hovertemplate='<b>%{label}</b><br>%{value:,.2f}₪<br>%{percent}<extra></extra>'
    )])

    fig.update_layout(
        title=title,
        showlegend=True,
        height=400,
        margin=dict(t=50, b=20, l=20, r=20)
    )

    return fig


def _empty_chart(title: str) -> go.Figure:
    """
    Create empty placeholder chart

    Args:
        title: Chart title

    Returns:
        Empty Plotly figure
    """
    fig = go.Figure()

    fig.add_annotation(
        text="No data available",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color=COLORS['gray'])
    )

    fig.update_layout(
        title=title,
        height=400,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        margin=dict(t=50, b=20, l=20, r=20)
    )

    return fig


def monthly_trend(
    data: pd.DataFrame,
    title: str = "Monthly Spending",
    date_col: str = "date",
    amount_col: str = "amount",
    months: int = 6
) -> go.Figure:
    """
    Create bar chart for monthly spending trend

    Args:
        data: DataFrame with transactions
        title: Chart title
        date_col: Column name for dates
        amount_col: Column name for amounts
        months: Number of recent months to show

    Returns:
        Plotly figure object
    """
    if data.empty:
        return _empty_chart(title)

    # Convert to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(data[date_col]):
        data = data.copy()
        data[date_col] = pd.to_datetime(data[date_col])

    # Group by month
    data = data.copy()
    data['month'] = data[date_col].dt.to_period('M')
    monthly = data.groupby('month')[amount_col].sum().abs()
    recent = monthly.tail(months)

    # Convert period to string for display
    x_labels = [str(m) for m in recent.index]

    fig = go.Figure(data=[go.Bar(
        x=x_labels,
        y=recent.values,
        marker=dict(color=COLORS['warning']),
        hovertemplate='%{x}<br>%{y:,.2f}₪<extra></extra>'
    )])

    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title="Spending (₪)",
        height=400,
        margin=dict(t=50, b=50, l=50, r=20),
        showlegend=False
    )

    return fig
