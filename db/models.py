"""
SQLAlchemy ORM models for financial data aggregator
"""

from datetime import datetime
from typing import Optional
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

    # Relationships
    account = relationship("Account", back_populates="transactions")

    __table_args__ = (
        Index('idx_transactions_account', 'account_id'),
        Index('idx_transactions_date', 'transaction_date'),
        Index('idx_transactions_status', 'status'),
        UniqueConstraint(
            'account_id', 'transaction_id', 'transaction_date', 'description', 'original_amount',
            name='uq_transaction'
        ),
    )

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
    metadata = Column(Text, nullable=True)  # JSON with additional info

    __table_args__ = (
        Index('idx_sync_history_date', 'started_at'),
        Index('idx_sync_history_status', 'status'),
    )

    def __repr__(self):
        return f"<SyncHistory(id={self.id}, type={self.sync_type}, status={self.status}, started={self.started_at})>"