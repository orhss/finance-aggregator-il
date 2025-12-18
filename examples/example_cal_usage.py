"""
Example usage of CAL Credit Card Scraper

This script demonstrates how to use the CAL scraper to fetch credit card transactions.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from scrapers.credit_cards.cal_credit_card_client import (
    CALCreditCardScraper,
    CALCredentials,
    TransactionStatus,
    TransactionType
)


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Create credentials from environment variables
    credentials = CALCredentials(
        username=os.getenv("CAL_USERNAME", ""),
        password=os.getenv("CAL_PASSWORD", "")
    )

    if not credentials.username or not credentials.password:
        print("Error: CAL_USERNAME and CAL_PASSWORD must be set in .env file")
        return

    # Initialize scraper (headless=False to see the browser)
    scraper = CALCreditCardScraper(credentials, headless=False)

    try:
        print("="*60)
        print("CAL Credit Card Transaction Scraper")
        print("="*60)

        # Option 1: Use the complete scrape() method (recommended)
        # This handles login and fetching in one call
        print("\nFetching transactions for the last 3 months...")
        accounts = scraper.scrape(months_back=3, months_forward=1)

        # Process and display results
        display_results(accounts)

        # Option 2: Manual control (for advanced usage)
        # scraper.setup_driver()
        # scraper.login()
        # accounts = scraper.fetch_transactions(months_back=3)
        # scraper.cleanup()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def display_results(accounts):
    """Display transaction results in a formatted way"""

    for account in accounts:
        print(f"\n{'='*60}")
        print(f"Card ending in: {account.account_number}")
        print(f"Card ID: {account.card_unique_id}")
        print(f"Total transactions: {len(account.transactions)}")
        print(f"{'='*60}")

        # Group transactions by status
        pending = [t for t in account.transactions if t.status == TransactionStatus.PENDING]
        completed = [t for t in account.transactions if t.status == TransactionStatus.COMPLETED]

        print(f"\nPending: {len(pending)} | Completed: {len(completed)}")

        # Calculate totals
        total_pending = sum(t.charged_amount for t in pending)
        total_completed = sum(t.charged_amount for t in completed)

        print(f"Total pending: {total_pending:,.2f} ILS")
        print(f"Total completed: {total_completed:,.2f} ILS")

        # Show recent transactions
        print(f"\n{'Recent Transactions':-^60}")
        print(f"{'Date':<12} {'Description':<30} {'Amount':>12} {'Status':<10}")
        print("-" * 60)

        # Sort by date descending
        sorted_txns = sorted(
            account.transactions,
            key=lambda t: t.date,
            reverse=True
        )

        for txn in sorted_txns[:20]:  # Show first 20
            date_str = txn.date[:10]
            desc = (txn.description[:27] + "...") if len(txn.description) > 30 else txn.description
            amount_str = f"{txn.charged_amount:>10.2f} {txn.original_currency}"

            print(f"{date_str:<12} {desc:<30} {amount_str:>12} {txn.status.value:<10}")

            # Show installment info if applicable
            if txn.installments:
                print(f"{'':12} └─ Installment {txn.installments.number}/{txn.installments.total}")

        # Export to CSV (optional)
        export_to_csv(account)


def export_to_csv(account):
    """Export transactions to CSV file"""
    import csv

    filename = f"cal_transactions_{account.account_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'Date',
            'Processed Date',
            'Description',
            'Original Amount',
            'Original Currency',
            'Charged Amount',
            'Charged Currency',
            'Status',
            'Type',
            'Category',
            'Installment',
            'Memo'
        ])

        # Transactions
        for txn in account.transactions:
            installment_info = ''
            if txn.installments:
                installment_info = f"{txn.installments.number}/{txn.installments.total}"

            writer.writerow([
                txn.date[:10],
                txn.processed_date[:10],
                txn.description,
                txn.original_amount,
                txn.original_currency,
                txn.charged_amount,
                txn.charged_currency or '',
                txn.status.value,
                txn.transaction_type.value,
                txn.category or '',
                installment_info,
                txn.memo or ''
            ])

    print(f"\nTransactions exported to: {filename}")


if __name__ == "__main__":
    main()