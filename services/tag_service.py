"""
Tag service for managing transaction tags and editing transactions
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from db.models import Tag, TransactionTag, Transaction, Account
from db.database import get_db

logger = logging.getLogger(__name__)


def _effective_amount_expr():
    """SQLAlchemy expression for effective amount: COALESCE(charged_amount, original_amount)"""
    return func.coalesce(Transaction.charged_amount, Transaction.original_amount)


class TagService:
    """
    Service for managing tags and editing transactions
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize tag service

        Args:
            session: SQLAlchemy session (if None, creates a new one)
        """
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> Session:
        """Get or create session"""
        if self._session is None:
            self._session = next(get_db())
        return self._session

    # ==================== Tag CRUD ====================

    def get_or_create_tag(self, name: str) -> Tag:
        """
        Get existing tag or create new one

        Args:
            name: Tag name (case-insensitive lookup, stored as-is)

        Returns:
            Tag object
        """
        name = name.strip()
        tag = self.session.query(Tag).filter(
            func.lower(Tag.name) == func.lower(name)
        ).first()

        if not tag:
            tag = Tag(name=name)
            self.session.add(tag)
            self.session.commit()
            logger.info(f"Created new tag: {name}")

        return tag

    def get_all_tags(self) -> List[Tag]:
        """
        Get all tags ordered by name

        Returns:
            List of Tag objects
        """
        return self.session.query(Tag).order_by(Tag.name).all()

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """
        Get tag by name (case-insensitive)

        Args:
            name: Tag name

        Returns:
            Tag object or None
        """
        return self.session.query(Tag).filter(
            func.lower(Tag.name) == func.lower(name.strip())
        ).first()

    def rename_tag(self, old_name: str, new_name: str) -> bool:
        """
        Rename a tag. If new_name exists, merges the tags.

        Args:
            old_name: Current tag name
            new_name: New tag name

        Returns:
            True if successful, False if old_name not found
        """
        old_tag = self.get_tag_by_name(old_name)
        if not old_tag:
            return False

        new_tag = self.get_tag_by_name(new_name)

        if new_tag and new_tag.id != old_tag.id:
            # Merge: move all transaction_tags to new_tag, delete old_tag
            for tt in old_tag.transaction_tags:
                # Check if transaction already has new_tag
                existing = self.session.query(TransactionTag).filter(
                    TransactionTag.transaction_id == tt.transaction_id,
                    TransactionTag.tag_id == new_tag.id
                ).first()

                if existing:
                    self.session.delete(tt)
                else:
                    tt.tag_id = new_tag.id

            self.session.delete(old_tag)
            logger.info(f"Merged tag '{old_name}' into '{new_name}'")
        else:
            # Simple rename
            old_tag.name = new_name.strip()
            logger.info(f"Renamed tag '{old_name}' to '{new_name}'")

        self.session.commit()
        return True

    def delete_tag(self, name: str) -> bool:
        """
        Delete a tag and all its associations

        Args:
            name: Tag name

        Returns:
            True if deleted, False if not found
        """
        tag = self.get_tag_by_name(name)
        if not tag:
            return False

        self.session.delete(tag)
        self.session.commit()
        logger.info(f"Deleted tag: {name}")
        return True

    # ==================== Transaction Tagging ====================

    def tag_transaction(self, transaction_id: int, tag_names: List[str]) -> int:
        """
        Add tags to a transaction

        Args:
            transaction_id: Transaction ID
            tag_names: List of tag names to add

        Returns:
            Number of tags added (excludes already existing)
        """
        transaction = self.session.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        added = 0
        for tag_name in tag_names:
            tag = self.get_or_create_tag(tag_name)

            # Check if already tagged
            existing = self.session.query(TransactionTag).filter(
                TransactionTag.transaction_id == transaction_id,
                TransactionTag.tag_id == tag.id
            ).first()

            if not existing:
                tt = TransactionTag(transaction_id=transaction_id, tag_id=tag.id)
                self.session.add(tt)
                added += 1

        self.session.commit()
        return added

    def untag_transaction(self, transaction_id: int, tag_names: List[str]) -> int:
        """
        Remove tags from a transaction

        Args:
            transaction_id: Transaction ID
            tag_names: List of tag names to remove

        Returns:
            Number of tags removed
        """
        removed = 0
        for tag_name in tag_names:
            tag = self.get_tag_by_name(tag_name)
            if not tag:
                continue

            tt = self.session.query(TransactionTag).filter(
                TransactionTag.transaction_id == transaction_id,
                TransactionTag.tag_id == tag.id
            ).first()

            if tt:
                self.session.delete(tt)
                removed += 1

        self.session.commit()
        return removed

    def get_transaction_tags(self, transaction_id: int) -> List[Tag]:
        """
        Get all tags for a transaction

        Args:
            transaction_id: Transaction ID

        Returns:
            List of Tag objects
        """
        return self.session.query(Tag).join(TransactionTag).filter(
            TransactionTag.transaction_id == transaction_id
        ).order_by(Tag.name).all()

    # ==================== Bulk Operations ====================

    def bulk_tag_by_merchant(self, merchant_pattern: str, tag_names: List[str]) -> int:
        """
        Tag all transactions matching merchant pattern

        Args:
            merchant_pattern: Pattern to match in description (case-insensitive)
            tag_names: List of tag names to add

        Returns:
            Number of transactions tagged
        """
        transactions = self.session.query(Transaction).filter(
            Transaction.description.ilike(f"%{merchant_pattern}%")
        ).all()

        count = 0
        for txn in transactions:
            added = self.tag_transaction(txn.id, tag_names)
            if added > 0:
                count += 1

        return count

    def bulk_tag_by_category(self, category: str, tag_names: List[str]) -> int:
        """
        Tag all transactions in a category

        Args:
            category: Category to match (case-insensitive)
            tag_names: List of tag names to add

        Returns:
            Number of transactions tagged
        """
        transactions = self.session.query(Transaction).filter(
            func.lower(Transaction.category) == func.lower(category)
        ).all()

        count = 0
        for txn in transactions:
            added = self.tag_transaction(txn.id, tag_names)
            if added > 0:
                count += 1

        return count

    # ==================== Transaction Editing ====================

    def update_transaction(
        self,
        transaction_id: int,
        user_category: Optional[str] = None,
        memo: Optional[str] = None
    ) -> bool:
        """
        Update transaction's user-editable fields

        Args:
            transaction_id: Transaction ID
            user_category: New user category (pass empty string to clear)
            memo: User notes/description override (pass empty string to clear)

        Returns:
            True if updated, False if not found
        """
        transaction = self.session.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

        if not transaction:
            return False

        if user_category is not None:
            transaction.user_category = user_category if user_category else None

        if memo is not None:
            transaction.memo = memo if memo else None

        self.session.commit()
        return True

    # ==================== Statistics ====================

    def get_tag_stats(self) -> List[Dict[str, Any]]:
        """
        Get usage statistics for all tags

        Returns:
            List of dicts: [{name, count, total_amount}, ...]
        """
        # Use effective amount (charged_amount if available, otherwise original_amount)
        # for proper installment handling
        results = self.session.query(
            Tag.name,
            func.count(TransactionTag.id).label('count'),
            func.coalesce(func.sum(_effective_amount_expr()), 0).label('total_amount')
        ).outerjoin(
            TransactionTag, Tag.id == TransactionTag.tag_id
        ).outerjoin(
            Transaction, TransactionTag.transaction_id == Transaction.id
        ).group_by(Tag.id).order_by(func.count(TransactionTag.id).desc()).all()

        return [
            {"name": r.name, "count": r.count, "total_amount": float(r.total_amount)}
            for r in results
        ]

    def get_untagged_count(self) -> int:
        """
        Get count of transactions without any tags

        Returns:
            Number of untagged transactions
        """
        tagged_ids = self.session.query(TransactionTag.transaction_id).distinct()
        return self.session.query(Transaction).filter(
            ~Transaction.id.in_(tagged_ids)
        ).count()

    def get_untagged_total(self) -> float:
        """
        Get total amount of untagged transactions

        Returns:
            Sum of effective amount (charged_amount if available, otherwise original_amount)
            for untagged transactions
        """
        tagged_ids = self.session.query(TransactionTag.transaction_id).distinct()
        result = self.session.query(
            func.coalesce(func.sum(_effective_amount_expr()), 0)
        ).filter(
            ~Transaction.id.in_(tagged_ids)
        ).scalar()
        return float(result)

    # ==================== Migration ====================

    def migrate_categories_to_tags(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Auto-tag all transactions based on their category

        Args:
            dry_run: If True, don't commit changes, just report what would happen

        Returns:
            Dict with category names and count of transactions that would be tagged
        """
        # Get all unique categories
        categories = self.session.query(Transaction.category).filter(
            Transaction.category.isnot(None),
            Transaction.category != ''
        ).distinct().all()

        results = {}

        for (category,) in categories:
            # Find transactions with this category that aren't tagged with it yet
            tag = self.get_tag_by_name(category)

            if tag:
                # Tag exists, find transactions not yet tagged
                tagged_ids = self.session.query(TransactionTag.transaction_id).filter(
                    TransactionTag.tag_id == tag.id
                )
                transactions = self.session.query(Transaction).filter(
                    Transaction.category == category,
                    ~Transaction.id.in_(tagged_ids)
                ).all()
            else:
                # Tag doesn't exist, all transactions with this category need tagging
                transactions = self.session.query(Transaction).filter(
                    Transaction.category == category
                ).all()

            if transactions:
                results[category] = len(transactions)

                if not dry_run:
                    for txn in transactions:
                        self.tag_transaction(txn.id, [category])

        if not dry_run:
            logger.info(f"Migrated categories to tags: {results}")

        return results

    def bulk_tag_by_card(self, card_last4: str, tag_name: str, dry_run: bool = False) -> int:
        """
        Tag all transactions from a specific card with the given tag

        Args:
            card_last4: Last 4 digits of the card (account_number)
            tag_name: Tag name to add (usually card holder name)
            dry_run: If True, don't commit changes, just return count

        Returns:
            Number of transactions tagged
        """
        # Find accounts with this card number
        accounts = self.session.query(Account).filter(
            Account.account_number == card_last4
        ).all()

        if not accounts:
            return 0

        account_ids = [a.id for a in accounts]

        # Get the tag (create if needed for dry run check)
        tag = self.get_tag_by_name(tag_name)

        if tag:
            # Find transactions not yet tagged
            tagged_ids = self.session.query(TransactionTag.transaction_id).filter(
                TransactionTag.tag_id == tag.id
            )
            transactions = self.session.query(Transaction).filter(
                Transaction.account_id.in_(account_ids),
                ~Transaction.id.in_(tagged_ids)
            ).all()
        else:
            # Tag doesn't exist, all transactions need tagging
            transactions = self.session.query(Transaction).filter(
                Transaction.account_id.in_(account_ids)
            ).all()

        if dry_run:
            return len(transactions)

        count = 0
        for txn in transactions:
            added = self.tag_transaction(txn.id, [tag_name])
            if added > 0:
                count += 1

        logger.info(f"Tagged {count} transactions from card ****{card_last4} with '{tag_name}'")
        return count