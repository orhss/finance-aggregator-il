"""
SQLAlchemy ORM models for financial data aggregator
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, Date, DateTime, Boolean,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Account(Base):
    """
    Stores account information across all institutions
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_type = Column(String(50), nullable=False)  # 'broker', 'pension', 'credit_card'
    institution = Column(String(100), nullable=False)  # 'excellence', 'migdal', 'phoenix', 'cal'
    account_number = Column(String(100), nullable=False)
    account_name = Column(String(255), nullable=True)
    card_unique_id = Column(String(100), nullable=True)  # For credit cards
    created_at = Column(DateTime, default=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    balances = relationship("Balance", back_populates="account", cascade="all, delete-orphan", order_by="desc(Balance.balance_date)")

    __table_args__ = (
        UniqueConstraint('account_type', 'institution', 'account_number', name='uq_account'),
    )

    @property
    def latest_balance(self) -> Optional['Balance']:
        """
        Get the most recent balance for this account.
        Single source of truth for balance access - apply masking/transforms here.
        """
        if not self.balances:
            return None
        return self.balances[0]  # Already sorted desc by balance_date

    def __repr__(self):
        return f"<Account(id={self.id}, type={self.account_type}, institution={self.institution}, number={self.account_number})>"


class Transaction(Base):
    """
    Unified transaction storage for all account types

    Category field hierarchy (priority order):
    1. user_category - Manual user override
    2. category - Normalized category from mapping table
    3. raw_category - Original category from provider API
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    transaction_id = Column(String(255), nullable=True)  # External transaction ID
    transaction_date = Column(Date, nullable=False)
    processed_date = Column(Date, nullable=True)
    description = Column(Text, nullable=False)
    original_amount = Column(Float, nullable=False)
    original_currency = Column(String(10), nullable=False)
    charged_amount = Column(Float, nullable=True)
    charged_currency = Column(String(10), nullable=True)
    transaction_type = Column(String(50), nullable=True)  # 'normal', 'installments', 'credit', 'debit'
    status = Column(String(50), nullable=True)  # 'pending', 'completed'
    raw_category = Column(String(255), nullable=True)  # Original category from provider
    category = Column(String(100), nullable=True)  # Normalized category (from mapping)
    memo = Column(Text, nullable=True)
    installment_number = Column(Integer, nullable=True)
    installment_total = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # User-editable fields (overrides for source data)
    user_category = Column(String(100), nullable=True)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    transaction_tags = relationship("TransactionTag", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_transactions_account', 'account_id'),
        Index('idx_transactions_date', 'transaction_date'),
        Index('idx_transactions_status', 'status'),
        Index('idx_transactions_raw_category', 'raw_category'),
        UniqueConstraint(
            'account_id', 'transaction_id', 'transaction_date', 'description', 'original_amount',
            name='uq_transaction'
        ),
    )

    @property
    def tags(self) -> List[str]:
        """Get list of tag names for this transaction"""
        return [tt.tag.name for tt in self.transaction_tags if tt.tag is not None]

    @property
    def effective_category(self) -> Optional[str]:
        """Get user category if set, then normalized category, then raw category"""
        return self.user_category or self.category or self.raw_category

    def __repr__(self):
        return f"<Transaction(id={self.id}, date={self.transaction_date}, description={self.description[:30]}, amount={self.original_amount})>"


class Balance(Base):
    """
    Snapshot of account balances (for broker/pension accounts)
    """
    __tablename__ = "balances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    balance_date = Column(Date, nullable=False)
    total_amount = Column(Float, nullable=False)
    available = Column(Float, nullable=True)
    used = Column(Float, nullable=True)
    blocked = Column(Float, nullable=True)
    profit_loss = Column(Float, nullable=True)
    profit_loss_percentage = Column(Float, nullable=True)
    currency = Column(String(10), default='ILS')
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="balances")

    __table_args__ = (
        Index('idx_balances_account', 'account_id'),
        Index('idx_balances_date', 'balance_date'),
        UniqueConstraint('account_id', 'balance_date', name='uq_balance'),
    )

    def __repr__(self):
        return f"<Balance(id={self.id}, account_id={self.account_id}, date={self.balance_date}, total={self.total_amount})>"


class SyncHistory(Base):
    """
    Track synchronization runs for debugging and monitoring
    """
    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(50), nullable=False)  # 'all', 'broker', 'pension', 'credit_card'
    institution = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False)  # 'success', 'failed', 'partial'
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    sync_metadata = Column(Text, nullable=True)  # JSON with additional info

    __table_args__ = (
        Index('idx_sync_history_date', 'started_at'),
        Index('idx_sync_history_status', 'status'),
    )

    def __repr__(self):
        return f"<SyncHistory(id={self.id}, type={self.sync_type}, status={self.status}, started={self.started_at})>"


class Tag(Base):
    """
    Tag for organizing transactions
    """
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transaction_tags = relationship("TransactionTag", back_populates="tag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tag(id={self.id}, name={self.name})>"


class TransactionTag(Base):
    """
    Many-to-many relationship between transactions and tags
    """
    __tablename__ = "transaction_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(Integer, ForeignKey('tags.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transaction = relationship("Transaction", back_populates="transaction_tags")
    tag = relationship("Tag", back_populates="transaction_tags")

    __table_args__ = (
        UniqueConstraint('transaction_id', 'tag_id', name='uq_transaction_tag'),
        Index('idx_transaction_tags_transaction', 'transaction_id'),
        Index('idx_transaction_tags_tag', 'tag_id'),
    )

    def __repr__(self):
        return f"<TransactionTag(transaction_id={self.transaction_id}, tag_id={self.tag_id})>"


class CategoryMapping(Base):
    """
    Maps provider-specific category names to unified category names.

    Each provider (CAL, Max, Isracard) uses different category names.
    This table normalizes them to a consistent set of unified categories.
    """
    __tablename__ = "category_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)  # 'cal', 'max', 'isracard'
    raw_category = Column(String(255), nullable=False)  # Original from provider
    unified_category = Column(String(100), nullable=False)  # Normalized name
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('provider', 'raw_category', name='uq_category_mapping'),
        Index('idx_category_mapping_lookup', 'provider', 'raw_category'),
    )

    def __repr__(self):
        return f"<CategoryMapping(provider={self.provider}, raw={self.raw_category}, unified={self.unified_category})>"


class MerchantMapping(Base):
    """
    Maps merchant patterns (from transaction descriptions) to unified category names.

    Used for transactions without provider categories (e.g., Isracard).
    Pattern matching is done on transaction description during sync.
    """
    __tablename__ = "merchant_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern = Column(String(255), nullable=False)  # Merchant pattern to match
    category = Column(String(100), nullable=False)  # Unified category name
    provider = Column(String(50), nullable=True)  # Optional: limit to specific provider
    match_type = Column(String(20), default='startswith')  # 'startswith', 'contains', 'exact'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('pattern', 'provider', name='uq_merchant_mapping'),
        Index('idx_merchant_mapping_pattern', 'pattern'),
        Index('idx_merchant_mapping_provider', 'provider'),
    )

    def matches(self, description: str) -> bool:
        """Check if this mapping matches the given description."""
        if not description:
            return False

        desc_lower = description.lower()
        pattern_lower = self.pattern.lower()

        if self.match_type == 'exact':
            return desc_lower == pattern_lower
        elif self.match_type == 'contains':
            return pattern_lower in desc_lower
        else:  # startswith (default)
            return desc_lower.startswith(pattern_lower)

    def __repr__(self):
        return f"<MerchantMapping(pattern={self.pattern}, category={self.category}, provider={self.provider})>"


class Budget(Base):
    """
    Monthly budget configuration.
    Simple year/month/amount model - no category budgets (KISS).
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('year', 'month', name='uq_budget_period'),
        Index('idx_budget_period', 'year', 'month'),
    )

    def __repr__(self):
        return f"<Budget(year={self.year}, month={self.month}, amount={self.amount})>"