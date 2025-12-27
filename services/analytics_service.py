"""
Analytics service for querying and analyzing financial data
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import func, extract, and_, or_
from sqlalchemy.orm import Session, joinedload
from db.models import Account, Transaction, Balance, SyncHistory, Tag, TransactionTag
from db.database import get_db


def get_effective_amount(txn: Transaction) -> float:
    """
    Get the effective amount for a transaction.
    Uses charged_amount (actual payment, e.g., per-installment) if available,
    otherwise falls back to original_amount (total purchase price).
    """
    if txn.charged_amount is not None:
        return txn.charged_amount
    return txn.original_amount or 0


# SQLAlchemy expression for effective amount in queries
# Use COALESCE(charged_amount, original_amount) for SQL aggregations
def effective_amount_expr():
    """SQLAlchemy expression for effective amount: COALESCE(charged_amount, original_amount)"""
    return func.coalesce(Transaction.charged_amount, Transaction.original_amount)


# SQLAlchemy expression for effective category in queries
# Use COALESCE(user_category, category) so user overrides take precedence
def effective_category_expr():
    """SQLAlchemy expression for effective category: COALESCE(user_category, category)"""
    return func.coalesce(Transaction.user_category, Transaction.category)


class AnalyticsService:
    """
    Service for querying and analyzing financial data
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize analytics service

        Args:
            session: SQLAlchemy session (if None, creates a new one)
        """
        self.session = session or next(get_db())

    # ==================== Account Methods ====================

    def get_all_accounts(self, active_only: bool = True) -> List[Account]:
        """
        Get all accounts

        Args:
            active_only: If True, only return active accounts

        Returns:
            List of Account objects
        """
        query = self.session.query(Account)
        if active_only:
            query = query.filter(Account.is_active == True)
        return query.order_by(Account.account_type, Account.institution).all()

    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """
        Get account by ID

        Args:
            account_id: Account ID

        Returns:
            Account object or None
        """
        return self.session.query(Account).filter(Account.id == account_id).first()

    def get_accounts_by_type(self, account_type: str, active_only: bool = True) -> List[Account]:
        """
        Get accounts by type

        Args:
            account_type: Account type ('broker', 'pension', 'credit_card')
            active_only: If True, only return active accounts

        Returns:
            List of Account objects
        """
        query = self.session.query(Account).filter(Account.account_type == account_type)
        if active_only:
            query = query.filter(Account.is_active == True)
        return query.order_by(Account.institution).all()

    def get_accounts_by_institution(self, institution: str, active_only: bool = True) -> List[Account]:
        """
        Get accounts by institution

        Args:
            institution: Institution name ('excellence', 'migdal', 'phoenix', 'cal')
            active_only: If True, only return active accounts

        Returns:
            List of Account objects
        """
        query = self.session.query(Account).filter(Account.institution == institution)
        if active_only:
            query = query.filter(Account.is_active == True)
        return query.order_by(Account.account_number).all()

    def get_account_summary(self) -> Dict[str, Any]:
        """
        Get summary of all accounts

        Returns:
            Dictionary with account counts by type and institution
        """
        accounts = self.get_all_accounts(active_only=True)

        summary = {
            "total_accounts": len(accounts),
            "by_type": {},
            "by_institution": {},
            "accounts": []
        }

        for account in accounts:
            # Count by type
            summary["by_type"][account.account_type] = summary["by_type"].get(account.account_type, 0) + 1

            # Count by institution
            summary["by_institution"][account.institution] = summary["by_institution"].get(account.institution, 0) + 1

            # Add account info
            summary["accounts"].append({
                "id": account.id,
                "type": account.account_type,
                "institution": account.institution,
                "account_number": account.account_number,
                "account_name": account.account_name,
                "last_synced": account.last_synced_at
            })

        return summary

    # ==================== Transaction Methods ====================

    def get_transactions(
        self,
        account_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[str] = None,
        institution: Optional[str] = None,
        tags: Optional[List[str]] = None,
        untagged_only: bool = False,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Transaction]:
        """
        Get transactions with filters

        Args:
            account_id: Filter by account ID
            from_date: Start date
            to_date: End date
            status: Transaction status ('pending', 'completed')
            institution: Filter by institution
            tags: Filter by tags (AND logic - must have all specified tags)
            untagged_only: If True, only return transactions without any tags
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Transaction objects
        """
        query = self.session.query(Transaction).join(Account)

        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        if from_date:
            query = query.filter(Transaction.transaction_date >= from_date)

        if to_date:
            query = query.filter(Transaction.transaction_date <= to_date)

        if status:
            query = query.filter(Transaction.status == status)

        if institution:
            query = query.filter(Account.institution == institution)

        # Tag filtering
        if untagged_only:
            # Get transactions that have no tags
            tagged_ids = self.session.query(TransactionTag.transaction_id).distinct()
            query = query.filter(~Transaction.id.in_(tagged_ids))
        elif tags:
            # Filter by tags (AND logic - must have all specified tags)
            for tag_name in tags:
                tag_subquery = (
                    self.session.query(TransactionTag.transaction_id)
                    .join(Tag)
                    .filter(func.lower(Tag.name) == func.lower(tag_name))
                )
                query = query.filter(Transaction.id.in_(tag_subquery))

        query = query.order_by(Transaction.transaction_date.desc())

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Get transaction by ID

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction object or None
        """
        return self.session.query(Transaction).filter(Transaction.id == transaction_id).first()

    def get_transaction_count(
        self,
        account_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Get count of transactions matching filters

        Args:
            account_id: Filter by account ID
            from_date: Start date
            to_date: End date
            status: Transaction status

        Returns:
            Count of transactions
        """
        query = self.session.query(func.count(Transaction.id))

        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        if from_date:
            query = query.filter(Transaction.transaction_date >= from_date)

        if to_date:
            query = query.filter(Transaction.transaction_date <= to_date)

        if status:
            query = query.filter(Transaction.status == status)

        return query.scalar()

    # ==================== Balance Methods ====================

    def get_latest_balances(self) -> List[Tuple[Account, Balance]]:
        """
        Get latest balance for each account

        Returns:
            List of (Account, Balance) tuples
        """
        # Subquery to get latest balance date for each account
        subquery = (
            self.session.query(
                Balance.account_id,
                func.max(Balance.balance_date).label('max_date')
            )
            .group_by(Balance.account_id)
            .subquery()
        )

        # Join to get the full balance records
        results = (
            self.session.query(Account, Balance)
            .join(Balance, Account.id == Balance.account_id)
            .join(
                subquery,
                and_(
                    Balance.account_id == subquery.c.account_id,
                    Balance.balance_date == subquery.c.max_date
                )
            )
            .order_by(Account.account_type, Account.institution)
            .all()
        )

        return results

    def get_balance_history(
        self,
        account_id: int,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[Balance]:
        """
        Get balance history for an account

        Args:
            account_id: Account ID
            from_date: Start date
            to_date: End date

        Returns:
            List of Balance objects
        """
        query = self.session.query(Balance).filter(Balance.account_id == account_id)

        if from_date:
            query = query.filter(Balance.balance_date >= from_date)

        if to_date:
            query = query.filter(Balance.balance_date <= to_date)

        return query.order_by(Balance.balance_date).all()

    def get_all_balances(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[Balance]:
        """
        Get all balance records across all accounts

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            List of Balance objects
        """
        query = self.session.query(Balance)

        if from_date:
            query = query.filter(Balance.balance_date >= from_date)

        if to_date:
            query = query.filter(Balance.balance_date <= to_date)

        return query.order_by(Balance.balance_date.desc()).all()

    # ==================== Statistics Methods ====================

    def get_overall_stats(self) -> Dict[str, Any]:
        """
        Get overall statistics

        Returns:
            Dictionary with various statistics
        """
        # Account stats
        total_accounts = self.session.query(func.count(Account.id)).filter(Account.is_active == True).scalar()

        # Transaction stats
        total_transactions = self.session.query(func.count(Transaction.id)).scalar()
        pending_transactions = self.session.query(func.count(Transaction.id)).filter(Transaction.status == 'pending').scalar()

        # Latest balances
        latest_balances = self.get_latest_balances()
        total_balance = sum(balance.total_amount for _, balance in latest_balances)

        # Last sync
        last_sync = (
            self.session.query(SyncHistory)
            .filter(SyncHistory.status == 'success')
            .order_by(SyncHistory.completed_at.desc())
            .first()
        )

        return {
            "total_accounts": total_accounts,
            "total_transactions": total_transactions,
            "pending_transactions": pending_transactions,
            "total_balance": total_balance,
            "last_sync": last_sync.completed_at if last_sync else None
        }

    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """
        Get monthly transaction summary

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Dictionary with monthly summary
        """
        # Get transactions for the month with eager-loaded accounts (fixes N+1 query)
        transactions = (
            self.session.query(Transaction)
            .options(joinedload(Transaction.account))
            .filter(
                extract('year', Transaction.transaction_date) == year,
                extract('month', Transaction.transaction_date) == month
            )
            .all()
        )

        total_amount = 0
        total_charged = 0
        transaction_count = len(transactions)

        by_status = {}
        by_type = {}
        by_account = {}

        for txn in transactions:
            # Sum amounts
            total_amount += abs(txn.original_amount or 0)
            if txn.charged_amount:
                total_charged += abs(txn.charged_amount)

            # Group by status
            status = txn.status or 'unknown'
            by_status[status] = by_status.get(status, 0) + 1

            # Group by type
            txn_type = txn.transaction_type or 'unknown'
            by_type[txn_type] = by_type.get(txn_type, 0) + 1

            # Group by account (account already loaded via joinedload)
            account = txn.account
            if account:
                key = f"{account.institution} ({account.account_type})"
                by_account[key] = by_account.get(key, 0) + 1

        return {
            "year": year,
            "month": month,
            "transaction_count": transaction_count,
            "total_amount": total_amount,
            "total_charged": total_charged,
            "by_status": by_status,
            "by_type": by_type,
            "by_account": by_account
        }

    def get_category_breakdown(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get transaction breakdown by category

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            Dictionary with category breakdown
        """
        query = self.session.query(Transaction)

        if from_date:
            query = query.filter(Transaction.transaction_date >= from_date)

        if to_date:
            query = query.filter(Transaction.transaction_date <= to_date)

        transactions = query.all()

        categories = {}
        for txn in transactions:
            # Use effective_category (user_category if set, otherwise original category)
            category = txn.effective_category or 'Uncategorized'

            if category not in categories:
                categories[category] = {
                    "count": 0,
                    "total_amount": 0,
                    "avg_amount": 0
                }

            categories[category]["count"] += 1
            # Use charged_amount (actual payment) if available, otherwise original_amount
            categories[category]["total_amount"] += abs(get_effective_amount(txn))

        # Calculate averages
        for category in categories:
            if categories[category]["count"] > 0:
                categories[category]["avg_amount"] = (
                    categories[category]["total_amount"] / categories[category]["count"]
                )

        return categories

    # ==================== Tag Analytics Methods ====================

    def get_tag_breakdown(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get transaction breakdown by tag

        Args:
            from_date: Start date filter
            to_date: End date filter

        Returns:
            Dictionary with tag breakdown: {tag_name: {count, total_amount, percentage}, ...}
            Includes special "(untagged)" key for transactions without tags
        """
        # Build base query for tagged transactions
        # Use effective_amount_expr() to get charged_amount if available, otherwise original_amount
        query = (
            self.session.query(
                Tag.name,
                func.count(Transaction.id).label('count'),
                func.coalesce(func.sum(effective_amount_expr()), 0).label('total_amount')
            )
            .join(TransactionTag, Tag.id == TransactionTag.tag_id)
            .join(Transaction, TransactionTag.transaction_id == Transaction.id)
        )

        if from_date:
            query = query.filter(Transaction.transaction_date >= from_date)
        if to_date:
            query = query.filter(Transaction.transaction_date <= to_date)

        query = query.group_by(Tag.id)
        tagged_results = query.all()

        # Get untagged transactions
        tagged_ids_subquery = self.session.query(TransactionTag.transaction_id).distinct()
        untagged_query = self.session.query(
            func.count(Transaction.id).label('count'),
            func.coalesce(func.sum(effective_amount_expr()), 0).label('total_amount')
        ).filter(~Transaction.id.in_(tagged_ids_subquery))

        if from_date:
            untagged_query = untagged_query.filter(Transaction.transaction_date >= from_date)
        if to_date:
            untagged_query = untagged_query.filter(Transaction.transaction_date <= to_date)

        untagged_result = untagged_query.first()

        # Calculate grand total for percentages
        grand_total = sum(abs(float(r.total_amount)) for r in tagged_results)
        if untagged_result and untagged_result.count > 0:
            grand_total += abs(float(untagged_result.total_amount))

        # Build result dictionary
        result = {}
        for r in tagged_results:
            amount = float(r.total_amount)
            percentage = (abs(amount) / grand_total * 100) if grand_total > 0 else 0
            result[r.name] = {
                'count': r.count,
                'total_amount': amount,
                'percentage': percentage
            }

        # Add untagged
        if untagged_result and untagged_result.count > 0:
            amount = float(untagged_result.total_amount)
            percentage = (abs(amount) / grand_total * 100) if grand_total > 0 else 0
            result['(untagged)'] = {
                'count': untagged_result.count,
                'total_amount': amount,
                'percentage': percentage
            }

        return result

    def get_monthly_tag_breakdown(self, year: int, month: int) -> Dict[str, Dict[str, Any]]:
        """
        Get monthly transaction breakdown by tag

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Dictionary with tag breakdown for the month
        """
        from calendar import monthrange

        # Calculate date range for the month
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        return self.get_tag_breakdown(from_date=first_day, to_date=last_day)

    def get_spending_for_tag(
        self,
        tag_name: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed spending breakdown for a specific tag

        Args:
            tag_name: Tag name to get spending for
            from_date: Start date filter
            to_date: End date filter

        Returns:
            Dictionary with:
            - total_amount: Total spending for this tag
            - count: Number of transactions
            - by_category: Breakdown by category {category: {count, total_amount}}
            - transactions: List of transaction details
        """
        # Find the tag
        tag = self.session.query(Tag).filter(
            func.lower(Tag.name) == func.lower(tag_name)
        ).first()

        if not tag:
            return {
                'total_amount': 0,
                'count': 0,
                'by_category': {},
                'transactions': []
            }

        # Get transactions for this tag
        query = (
            self.session.query(Transaction)
            .join(TransactionTag, Transaction.id == TransactionTag.transaction_id)
            .filter(TransactionTag.tag_id == tag.id)
        )

        if from_date:
            query = query.filter(Transaction.transaction_date >= from_date)
        if to_date:
            query = query.filter(Transaction.transaction_date <= to_date)

        query = query.order_by(Transaction.transaction_date.desc())
        transactions = query.all()

        # Calculate totals and category breakdown
        # Use effective amount (charged_amount if available, otherwise original_amount)
        total_amount = 0
        by_category: Dict[str, Dict[str, Any]] = {}

        for txn in transactions:
            effective_amt = get_effective_amount(txn)
            total_amount += effective_amt
            # Use effective_category (user_category if set, otherwise original category)
            category = txn.effective_category or '(uncategorized)'

            if category not in by_category:
                by_category[category] = {'count': 0, 'total_amount': 0}

            by_category[category]['count'] += 1
            by_category[category]['total_amount'] += effective_amt

        # Build transaction list
        txn_list = [
            {
                'id': txn.id,
                'date': txn.transaction_date,
                'description': txn.description,
                'amount': get_effective_amount(txn),
                'currency': txn.charged_currency or txn.original_currency,
                'category': txn.effective_category or '(uncategorized)'
            }
            for txn in transactions
        ]

        return {
            'total_amount': total_amount,
            'count': len(transactions),
            'by_category': by_category,
            'transactions': txn_list
        }

    # ==================== Sync History Methods ====================

    # ==================== Spending Trends Methods ====================

    def get_monthly_spending_trends(
        self,
        months: int = 6,
        tag: Optional[str] = None,
        card_last4: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get monthly spending totals for trend analysis

        Args:
            months: Number of months to include (default 6)
            tag: Optional tag filter
            card_last4: Optional filter by card last 4 digits (account_number)

        Returns:
            List of dicts with: year, month, total_amount, transaction_count
            Ordered from oldest to newest
        """
        from dateutil.relativedelta import relativedelta

        # Calculate date range
        today = date.today()
        # Start from beginning of (months-1) months ago to include current month
        start_date = date(today.year, today.month, 1) - relativedelta(months=months - 1)

        # Build query - use effective_amount_expr for proper installment handling
        query = self.session.query(
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(effective_amount_expr()).label('total_amount'),
            func.count(Transaction.id).label('transaction_count')
        ).filter(
            Transaction.transaction_date >= start_date
        )

        # Apply tag filter
        if tag:
            tag_obj = self.session.query(Tag).filter(
                func.lower(Tag.name) == func.lower(tag)
            ).first()
            if tag_obj:
                query = query.join(
                    TransactionTag, Transaction.id == TransactionTag.transaction_id
                ).filter(TransactionTag.tag_id == tag_obj.id)
            else:
                return []

        # Apply card holder filter (last 4 digits = account_number)
        if card_last4:
            query = query.join(Account, Transaction.account_id == Account.id).filter(
                Account.account_number == card_last4
            )

        query = query.group_by(
            extract('year', Transaction.transaction_date),
            extract('month', Transaction.transaction_date)
        ).order_by(
            extract('year', Transaction.transaction_date),
            extract('month', Transaction.transaction_date)
        )

        results = query.all()

        # Convert to list of dicts
        monthly_data = []
        for r in results:
            monthly_data.append({
                'year': int(r.year),
                'month': int(r.month),
                'total_amount': float(r.total_amount) if r.total_amount else 0,
                'transaction_count': r.transaction_count
            })

        return monthly_data

    def get_category_trends(
        self,
        months: int = 6,
        top_n: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get spending trends by category over multiple months

        Args:
            months: Number of months to analyze
            top_n: Number of top categories to return

        Returns:
            Dict with category name as key, list of monthly amounts as value
            Plus 'totals' key with overall totals per category
        """
        from dateutil.relativedelta import relativedelta

        today = date.today()
        start_date = date(today.year, today.month, 1) - relativedelta(months=months - 1)

        # Get category totals to find top N
        # Use effective_category_expr (user_category if set, otherwise category)
        # Use effective_amount_expr for proper installment handling
        eff_category = effective_category_expr()
        category_totals = self.session.query(
            eff_category.label('category'),
            func.sum(func.abs(effective_amount_expr())).label('total')
        ).filter(
            Transaction.transaction_date >= start_date,
            eff_category.isnot(None)
        ).group_by(
            eff_category
        ).order_by(
            func.sum(func.abs(effective_amount_expr())).desc()
        ).limit(top_n).all()

        top_categories = [c.category for c in category_totals]

        if not top_categories:
            return {'categories': {}, 'totals': {}}

        # Get monthly breakdown for top categories
        # Use effective_category_expr and effective_amount_expr
        monthly_query = self.session.query(
            eff_category.label('category'),
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(effective_amount_expr()).label('amount')
        ).filter(
            Transaction.transaction_date >= start_date,
            eff_category.in_(top_categories)
        ).group_by(
            eff_category,
            extract('year', Transaction.transaction_date),
            extract('month', Transaction.transaction_date)
        ).all()

        # Organize by category
        categories: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in top_categories}
        for r in monthly_query:
            categories[r.category].append({
                'year': int(r.year),
                'month': int(r.month),
                'amount': abs(float(r.amount)) if r.amount else 0
            })

        # Sort each category's data by date
        for cat in categories:
            categories[cat].sort(key=lambda x: (x['year'], x['month']))

        # Build totals dict
        totals = {c.category: float(c.total) for c in category_totals}

        return {'categories': categories, 'totals': totals}

    def get_spending_by_card_holder(
        self,
        months: int = 6
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get spending breakdown by card holder (last 4 digits = account_number)

        Args:
            months: Number of months to include

        Returns:
            Dict with last4 as key, {total_amount, transaction_count, percentage} as value
        """
        from dateutil.relativedelta import relativedelta

        today = date.today()
        start_date = date(today.year, today.month, 1) - relativedelta(months=months - 1)

        # Query transactions grouped by account_number (which is the last 4 digits for credit cards)
        # Use effective_amount_expr for proper installment handling
        results = self.session.query(
            Account.account_number,
            func.sum(func.abs(effective_amount_expr())).label('total_amount'),
            func.count(Transaction.id).label('transaction_count')
        ).join(
            Transaction, Account.id == Transaction.account_id
        ).filter(
            Transaction.transaction_date >= start_date,
            Account.account_type == 'credit_card'
        ).group_by(
            Account.account_number
        ).all()

        # Calculate grand total
        grand_total = sum(float(r.total_amount or 0) for r in results)

        # Build result dict
        by_card: Dict[str, Dict[str, Any]] = {}
        for r in results:
            last4 = r.account_number
            total = float(r.total_amount or 0)
            by_card[last4] = {
                'total_amount': total,
                'transaction_count': r.transaction_count,
                'percentage': (total / grand_total * 100) if grand_total > 0 else 0
            }

        return by_card

    # ==================== Sync History Methods ====================

    def get_sync_history(
        self,
        limit: int = 10,
        institution: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[SyncHistory]:
        """
        Get sync history

        Args:
            limit: Maximum number of results
            institution: Filter by institution
            status: Filter by status

        Returns:
            List of SyncHistory objects
        """
        query = self.session.query(SyncHistory)

        if institution:
            query = query.filter(SyncHistory.institution == institution)

        if status:
            query = query.filter(SyncHistory.status == status)

        return query.order_by(SyncHistory.started_at.desc()).limit(limit).all()

    def close(self):
        """Close the database session"""
        if self.session:
            self.session.close()