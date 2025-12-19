"""
Analytics service for querying and analyzing financial data
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import func, extract, and_, or_
from sqlalchemy.orm import Session
from db.models import Account, Transaction, Balance, SyncHistory
from db.database import get_db


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
        # Get transactions for the month
        transactions = (
            self.session.query(Transaction)
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

            # Group by account
            account = self.get_account_by_id(txn.account_id)
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
            category = txn.category or 'Uncategorized'

            if category not in categories:
                categories[category] = {
                    "count": 0,
                    "total_amount": 0,
                    "avg_amount": 0
                }

            categories[category]["count"] += 1
            categories[category]["total_amount"] += abs(txn.original_amount or 0)

        # Calculate averages
        for category in categories:
            if categories[category]["count"] > 0:
                categories[category]["avg_amount"] = (
                    categories[category]["total_amount"] / categories[category]["count"]
                )

        return categories

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