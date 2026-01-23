"""
Caching utilities for Streamlit UI performance optimization.

Provides centralized caching functions for expensive database queries with configurable TTL.
"""

import streamlit as st
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, datetime, timedelta
import pandas as pd


@st.cache_data(ttl=300, show_spinner=False)
def get_transactions_cached(
    start_date: date,
    end_date: date,
    account_ids: Optional[Tuple[int, ...]] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    institution: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Cached transaction query - returns serializable data.

    Args:
        start_date: Start date for transactions
        end_date: End date for transactions
        account_ids: Optional tuple of account IDs (must be tuple for hashability)
        status: Optional status filter (pending/completed)
        category: Optional category filter
        institution: Optional institution filter

    Returns:
        List of transaction dictionaries

    Cache: 5 minutes TTL
    """
    from db.database import get_session
    from db.models import Transaction, Account
    from sqlalchemy import and_

    session = get_session()
    try:
        query = session.query(Transaction).join(Account).filter(
            Transaction.transaction_date.between(start_date, end_date)
        )

        if account_ids:
            query = query.filter(Transaction.account_id.in_(account_ids))
        if status:
            query = query.filter(Transaction.status == status)
        if category:
            query = query.filter(Transaction.effective_category == category)
        if institution:
            query = query.filter(Account.institution == institution)

        # Return dicts, not ORM objects (for caching)
        transactions = []
        for t in query.all():
            transactions.append({
                'id': t.id,
                'transaction_date': t.transaction_date,
                'description': t.description,
                'original_amount': float(t.original_amount) if t.original_amount else 0.0,
                'charged_amount': float(t.charged_amount) if t.charged_amount else 0.0,
                'effective_category': t.effective_category,
                'status': t.status,
                'account_id': t.account_id,
                'institution': t.account.institution if t.account else None,
                'memo': t.memo,
                'installment_number': t.installment_number,
                'installment_total': t.installment_total,
                'transaction_type': t.transaction_type,
                'tags': t.tags  # t.tags property already returns list of strings
            })

        return transactions
    finally:
        session.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_dashboard_stats(months_back: int = 3) -> Dict[str, Any]:
    """
    Cached dashboard statistics query.

    Args:
        months_back: Number of months of data to include

    Returns:
        Dictionary with dashboard statistics

    Cache: 1 minute TTL
    """
    from db.database import get_session
    from db.models import Transaction, Account
    from sqlalchemy import func, and_
    from datetime import date, timedelta

    session = get_session()
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=30 * months_back)

        # Total portfolio value (latest balances via Account.latest_balance)
        accounts = session.query(Account).all()
        latest_balances = sum(
            acc.latest_balance.total_amount
            for acc in accounts
            if acc.latest_balance is not None
        ) or 0.0

        # Monthly spending (current month, expenses only)
        month_start = date.today().replace(day=1)
        monthly_spending = session.query(
            func.sum(Transaction.original_amount)
        ).filter(
            and_(
                Transaction.transaction_date >= month_start,
                Transaction.original_amount < 0,
                Transaction.status == 'completed'
            )
        ).scalar() or 0.0

        # Pending transactions
        pending_count = session.query(func.count(Transaction.id)).filter(
            Transaction.status == 'pending'
        ).scalar() or 0

        pending_amount = session.query(
            func.sum(Transaction.original_amount)
        ).filter(
            Transaction.status == 'pending'
        ).scalar() or 0.0

        # Last sync time (most recent transaction creation time as proxy)
        last_sync = session.query(func.max(Transaction.created_at)).scalar()

        # Account count
        account_count = session.query(func.count(Account.id)).scalar() or 0

        # Transaction count (period)
        transaction_count = session.query(func.count(Transaction.id)).filter(
            Transaction.transaction_date.between(start_date, end_date)
        ).scalar() or 0

        return {
            'total_balance': float(latest_balances),
            'monthly_spending': abs(float(monthly_spending)),
            'pending_count': pending_count,
            'pending_amount': float(pending_amount),
            'last_sync': last_sync,
            'account_count': account_count,
            'transaction_count': transaction_count,
            'period_start': start_date,
            'period_end': end_date
        }
    finally:
        session.close()


@st.cache_data(ttl=300, show_spinner=False)
def get_category_spending_cached(
    start_date: date,
    end_date: date,
    top_n: Optional[int] = None
) -> pd.DataFrame:
    """
    Cached category spending aggregation.

    Args:
        start_date: Start date
        end_date: End date
        top_n: Optional limit to top N categories

    Returns:
        DataFrame with category spending data

    Cache: 5 minutes TTL
    """
    from db.database import get_session
    from db.models import Transaction
    from sqlalchemy import func, and_

    session = get_session()
    try:
        query = session.query(
            Transaction.effective_category,
            func.sum(Transaction.original_amount).label('total'),
            func.count(Transaction.id).label('count')
        ).filter(
            and_(
                Transaction.transaction_date.between(start_date, end_date),
                Transaction.original_amount < 0,  # Expenses only
                Transaction.status == 'completed'
            )
        ).group_by(Transaction.effective_category)

        if top_n:
            query = query.order_by(func.sum(Transaction.original_amount).asc()).limit(top_n)

        results = query.all()

        df = pd.DataFrame([
            {
                'category': r.effective_category or 'Uncategorized',
                'amount': abs(float(r.total)),
                'count': r.count
            }
            for r in results
        ])

        return df
    finally:
        session.close()


@st.cache_data(ttl=300, show_spinner=False)
def get_monthly_trend_cached(months_back: int = 6) -> pd.DataFrame:
    """
    Cached monthly spending trend data.

    Args:
        months_back: Number of months to include

    Returns:
        DataFrame with monthly trend data

    Cache: 5 minutes TTL
    """
    from db.database import get_session
    from db.models import Transaction
    from sqlalchemy import func, extract, and_

    session = get_session()
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=30 * months_back)

        query = session.query(
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(Transaction.original_amount).label('total'),
            func.count(Transaction.id).label('count')
        ).filter(
            and_(
                Transaction.transaction_date.between(start_date, end_date),
                Transaction.original_amount < 0,  # Expenses only
                Transaction.status == 'completed'
            )
        ).group_by('year', 'month').order_by('year', 'month')

        results = query.all()

        df = pd.DataFrame([
            {
                'year': int(r.year),
                'month': int(r.month),
                'amount': abs(float(r.total)),
                'count': r.count,
                'month_name': datetime(int(r.year), int(r.month), 1).strftime('%b %Y')
            }
            for r in results
        ])

        return df
    finally:
        session.close()


@st.cache_data(ttl=300, show_spinner=False)
def get_accounts_cached() -> List[Dict[str, Any]]:
    """
    Cached accounts query with latest balances.

    Returns:
        List of account dictionaries with balance info

    Cache: 5 minutes TTL
    """
    from db.database import get_session
    from db.models import Account

    session = get_session()
    try:
        accounts = session.query(Account).all()

        result = []
        for acc in accounts:
            # Use account.latest_balance (single source of truth)
            latest_balance = acc.latest_balance

            result.append({
                'id': acc.id,
                'account_number': acc.account_number,
                'account_name': acc.account_name,
                'institution': acc.institution,
                'account_type': acc.account_type,
                'is_active': acc.is_active,
                'latest_balance': float(latest_balance.total_amount) if latest_balance else 0.0,
                'latest_balance_date': latest_balance.balance_date if latest_balance else None,
                'created_at': acc.created_at,
                'last_synced_at': acc.last_synced_at
            })

        return result
    finally:
        session.close()


@st.cache_data(ttl=300, show_spinner=False)
def get_tags_cached() -> List[Dict[str, Any]]:
    """
    Cached tags query with usage statistics.

    Returns:
        List of tag dictionaries with usage stats

    Cache: 5 minutes TTL
    """
    from db.database import get_session
    from db.models import Tag, Transaction
    from sqlalchemy import func

    session = get_session()
    try:
        # Query tags with transaction count and total amount
        query = session.query(
            Tag.id,
            Tag.name,
            func.count(Transaction.id).label('transaction_count'),
            func.sum(Transaction.original_amount).label('total_amount')
        ).outerjoin(Tag.transactions).group_by(Tag.id, Tag.name)

        results = query.all()

        tags = []
        for r in results:
            tags.append({
                'id': r.id,
                'name': r.name,
                'transaction_count': r.transaction_count or 0,
                'total_amount': abs(float(r.total_amount)) if r.total_amount else 0.0
            })

        return tags
    finally:
        session.close()


def invalidate_all_caches():
    """Clear all Streamlit caches. Call after sync or data modifications."""
    st.cache_data.clear()


def invalidate_transaction_cache():
    """Clear transaction-related caches. Call after transaction edits."""
    from streamlit_app.utils.session import get_all_categories
    get_transactions_cached.clear()
    get_category_spending_cached.clear()
    get_monthly_trend_cached.clear()
    get_dashboard_stats.clear()
    get_all_categories.clear()  # Categories come from transactions


def invalidate_account_cache():
    """Clear account-related caches. Call after account changes."""
    get_accounts_cached.clear()
    get_dashboard_stats.clear()


def invalidate_tag_cache():
    """Clear tag-related caches. Call after tag changes."""
    from streamlit_app.utils.session import get_all_tags
    get_tags_cached.clear()
    get_all_tags.clear()
