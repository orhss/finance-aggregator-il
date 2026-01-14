"""
Calendar Heatmap Component - GitHub-style spending visualization
"""

import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from typing import Optional
import calendar


def calendar_heatmap(
    data: pd.DataFrame,
    date_col: str = 'date',
    value_col: str = 'amount',
    year: Optional[int] = None,
    title: str = "Daily Spending Heatmap",
    colorscale: str = 'Greens'
) -> go.Figure:
    """
    Create GitHub-style calendar heatmap for daily spending visualization.

    Args:
        data: DataFrame with date and value columns
        date_col: Name of date column
        value_col: Name of value column (spending amounts)
        year: Year to display (defaults to current year)
        title: Chart title
        colorscale: Plotly colorscale name

    Returns:
        Plotly figure object with heatmap
    """
    year = year or date.today().year

    # Create date range for the year
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    # Aggregate spending by day (absolute values for expenses)
    data_copy = data.copy()
    data_copy[date_col] = pd.to_datetime(data_copy[date_col])
    data_copy['date_only'] = data_copy[date_col].dt.date
    daily = data_copy.groupby('date_only')[value_col].sum().abs()

    # Build calendar structure (weeks x days)
    # Start from first Monday before/on Jan 1
    first_day = start
    while first_day.weekday() != 0:  # 0 = Monday
        first_day = first_day - timedelta(days=1)

    # Build week structure
    weeks = []
    current_date = first_day
    current_week = []

    while current_date <= end + timedelta(days=6):  # Extra week buffer
        # Add day to current week
        value = daily.get(current_date, 0) if start <= current_date <= end else None
        current_week.append({
            'date': current_date,
            'value': value,
            'weekday': current_date.weekday(),
            'month': current_date.month
        })

        # Start new week on Monday
        if current_date.weekday() == 6:  # Sunday
            weeks.append(current_week)
            current_week = []

        current_date += timedelta(days=1)

    if current_week:  # Add remaining days
        weeks.append(current_week)

    # Build heatmap matrix (7 rows = days of week, N cols = weeks)
    z = [[None] * len(weeks) for _ in range(7)]
    text = [['' for _ in range(len(weeks))] for _ in range(7)]
    customdata = [['' for _ in range(len(weeks))] for _ in range(7)]

    for week_idx, week in enumerate(weeks):
        for day in week:
            if day['value'] is not None:
                weekday = day['weekday']
                z[weekday][week_idx] = day['value']
                text[weekday][week_idx] = f"{day['date'].strftime('%Y-%m-%d')}"
                customdata[weekday][week_idx] = f"₪{day['value']:,.0f}"

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=z,
        text=text,
        customdata=customdata,
        hovertemplate='<b>%{text}</b><br>Spending: %{customdata}<extra></extra>',
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(
            title=dict(text="Spending (₪)", side="right"),
            tickformat=",.0f"
        ),
        xgap=3,  # Gap between cells
        ygap=3
    ))

    # Update layout
    fig.update_layout(
        title=title,
        yaxis=dict(
            ticktext=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            tickvals=list(range(7)),
            tickmode='array',
            side='left'
        ),
        xaxis=dict(
            title='',
            tickmode='array',
            tickvals=list(range(0, len(weeks), 4)),  # Show every 4th week
            ticktext=[f"Week {i+1}" for i in range(0, len(weeks), 4)],
            side='bottom'
        ),
        height=250,
        margin=dict(t=50, b=30, l=60, r=100),
        plot_bgcolor='white'
    )

    # Add month labels at top
    month_positions = {}
    for week_idx, week in enumerate(weeks):
        for day in week:
            if day['value'] is not None:
                month = day['month']
                if month not in month_positions or week_idx < month_positions[month]:
                    month_positions[month] = week_idx

    # Add month annotations
    for month, week_idx in month_positions.items():
        month_name = calendar.month_abbr[month]
        fig.add_annotation(
            x=week_idx,
            y=-0.5,
            text=month_name,
            showarrow=False,
            font=dict(size=10, color='gray'),
            xref='x',
            yref='y'
        )

    return fig


def monthly_heatmap(
    data: pd.DataFrame,
    date_col: str = 'date',
    value_col: str = 'amount',
    year: Optional[int] = None,
    title: str = "Monthly Spending Heatmap"
) -> go.Figure:
    """
    Create monthly heatmap showing spending by day of month.

    Args:
        data: DataFrame with date and value columns
        date_col: Name of date column
        value_col: Name of value column
        year: Year to display (defaults to current year)
        title: Chart title

    Returns:
        Plotly figure object
    """
    year = year or date.today().year

    # Filter data for year
    data_copy = data.copy()
    data_copy[date_col] = pd.to_datetime(data_copy[date_col])
    data_year = data_copy[data_copy[date_col].dt.year == year].copy()

    if data_year.empty:
        # Return empty chart
        fig = go.Figure()
        fig.update_layout(
            title=title,
            annotations=[dict(
                text=f"No data for {year}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )],
            height=400
        )
        return fig

    # Add month and day columns
    data_year['month'] = data_year[date_col].dt.month
    data_year['day'] = data_year[date_col].dt.day

    # Aggregate by month and day
    pivot = data_year.groupby(['month', 'day'])[value_col].sum().abs().reset_index()
    pivot_table = pivot.pivot(index='day', columns='month', values=value_col).fillna(0)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=[calendar.month_abbr[m] for m in pivot_table.columns],
        y=pivot_table.index,
        colorscale='Reds',
        hovertemplate='<b>%{x} %{y}</b><br>₪%{z:,.0f}<extra></extra>',
        colorbar=dict(title="Spending (₪)")
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title="Day of Month",
        height=500,
        yaxis=dict(autorange='reversed')  # Day 1 at top
    )

    return fig
