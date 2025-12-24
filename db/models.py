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
    balances = relationship("Balance", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('account_type', 'institution', 'account_number', name='uq_account'),
    )

    def __repr__(self):
        return f"<Account(id={self.id}, type={self.account_type}, institution={self.institution}, number={self.account_number})>"


class Transaction(Base):
    """
    Unified transaction storage for all account types
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
    category = Column(String(100), nullable=True)
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
        UniqueConstraint(
            'account_id', 'transaction_id', 'transaction_date', 'description', 'original_amount',
            name='uq_transaction'
        ),
    )

    @property
    def tags(self) -> List[str]:
        """Get list of tag names for this transaction"""
        return [tt.tag.name for tt in self.transaction_tags]

    @property
    def effective_category(self) -> Optional[str]:
        """Get user category if set, otherwise source category"""
        return self.user_category or self.category

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