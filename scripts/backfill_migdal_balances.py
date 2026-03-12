"""
One-off script to backfill historic Migdal pension balances.

Usage:
    python scripts/backfill_migdal_balances.py          # dry run (default)
    python scripts/backfill_migdal_balances.py --apply   # actually insert
"""

import sys
from datetime import date

# ── Account 1: Migdal Pension (200361749) ───────────────────────
PENSION_1_ACCOUNT_ID = 1
PENSION_1_BALANCES = [
    ("2022-09-30", 356609),
    ("2022-10-31", 362609),
    ("2022-11-30", 369609),
    ("2022-12-31", 377864),
    ("2023-01-31", 448732),
    ("2023-02-28", 448732),
    ("2023-03-31", 448732),
    ("2023-04-30", 486285),
    ("2023-05-31", 486285),
    ("2023-06-30", 486285),
    ("2023-07-31", 495285),
    ("2023-08-31", 500285),
    ("2023-09-30", 506980),
    ("2023-10-31", 516980),
    ("2023-11-30", 526980),
    ("2023-12-31", 545365),
    ("2024-01-31", 560365),
    ("2024-02-29", 580365),
    ("2024-03-31", 610000),
    ("2024-04-30", 618000),
    ("2024-05-31", 618000),
    ("2024-06-30", 670654),
    ("2024-07-31", 657760),
    ("2024-08-31", 695131),
    ("2024-09-30", 717252),
    ("2024-10-31", 737913),
    ("2024-11-30", 749762),
    ("2024-12-31", 759615),
    ("2025-01-31", 762038),
    ("2025-02-28", 762844),
    ("2025-03-31", 763364),
    ("2025-04-30", 736229),
    ("2025-05-31", 782033),
    ("2025-06-30", 792000),
    ("2025-07-31", 804931),
    ("2025-08-31", 831218),
    ("2025-09-30", 853479),
    ("2025-10-31", 860237),
    ("2025-11-30", 878098),
]

# ── Account: Migdal Pension 2 (203139803) — needs to be created ─
PENSION_2_ACCOUNT_NUMBER = "203139803"
PENSION_2_ACCOUNT_NAME = "Migdal Pension 2"
PENSION_2_BALANCES = [
    ("2022-09-30", 207003),
    ("2022-10-31", 207003),
    ("2022-11-30", 207003),
    ("2022-12-31", 207003),
    ("2023-01-31", 207003),
    ("2023-02-28", 207003),
    ("2023-03-31", 207003),
    ("2023-04-30", 207003),
    ("2023-05-31", 207003),
    ("2023-06-30", 207003),
    ("2023-07-31", 207003),
    ("2023-08-31", 207003),
    ("2023-09-30", 207003),
    ("2023-10-31", 207003),
    ("2023-11-30", 207003),
    ("2023-12-31", 288248),
    ("2024-01-31", 294000),
    ("2024-02-29", 300000),
    ("2024-03-31", 315000),
    ("2024-04-30", 323472),
    ("2024-05-31", 323472),
    ("2024-06-30", 323472),
    ("2024-07-31", 323472),
    ("2024-08-31", 358860),
    ("2024-09-30", 375286),
    ("2024-10-31", 383133),
    ("2024-11-30", 393631),
    ("2024-12-31", 400371),
    ("2025-01-31", 402847),
    ("2025-02-28", 403500),
    ("2025-03-31", 410556),
    ("2025-04-30", 406118),
    ("2025-05-31", 424214),
    ("2025-06-30", 431080),
    ("2025-07-31", 446064),
    ("2025-08-31", 455360),
    ("2025-09-30", 467905),
    ("2025-10-31", 472260),
    ("2025-11-30", 482643),
    ("2025-12-31", 478000),
    ("2026-01-31", 471643),
    ("2026-02-28", 464446),
]


def backfill_account(session, account_id, balances, label, apply):
    """Insert balances for an existing account."""
    from db.models import Balance

    inserted, skipped = 0, 0
    print(f"\n── {label} (account_id={account_id}) ──")

    for date_str, amount in balances:
        bal_date = date.fromisoformat(date_str)

        existing = session.query(Balance).filter(
            Balance.account_id == account_id,
            Balance.balance_date == bal_date,
        ).first()

        if existing:
            print(f"  SKIP {date_str} — already exists (₪{existing.total_amount:,.0f})")
            skipped += 1
            continue

        if apply:
            balance = Balance(
                account_id=account_id,
                balance_date=bal_date,
                total_amount=amount,
            )
            session.add(balance)
            print(f"  INSERT {date_str} → ₪{amount:,.0f}")
        else:
            print(f"  WOULD INSERT {date_str} → ₪{amount:,.0f}")
        inserted += 1

    return inserted, skipped


def main():
    apply = "--apply" in sys.argv

    from datetime import datetime
    from db.database import create_database_engine
    from sqlalchemy.orm import sessionmaker
    from db.models import Account, Balance

    engine = create_database_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    total_inserted, total_skipped = 0, 0

    # ── Pension 1: existing account ──
    ins, skip = backfill_account(
        session, PENSION_1_ACCOUNT_ID, PENSION_1_BALANCES,
        "Migdal Pension (200361749)", apply,
    )
    total_inserted += ins
    total_skipped += skip

    # ── Pension 2: create account if needed ──
    account2 = session.query(Account).filter(
        Account.institution == "migdal",
        Account.account_number == PENSION_2_ACCOUNT_NUMBER,
    ).first()

    if not account2:
        if apply:
            account2 = Account(
                account_type="pension",
                institution="migdal",
                account_number=PENSION_2_ACCOUNT_NUMBER,
                account_name=PENSION_2_ACCOUNT_NAME,
                last_synced_at=datetime.utcnow(),
            )
            session.add(account2)
            session.flush()
            print(f"\nCREATED account: {PENSION_2_ACCOUNT_NAME} ({PENSION_2_ACCOUNT_NUMBER}) → id={account2.id}")
        else:
            print(f"\nWOULD CREATE account: {PENSION_2_ACCOUNT_NAME} ({PENSION_2_ACCOUNT_NUMBER})")
    else:
        print(f"\nAccount already exists: {account2.account_name} → id={account2.id}")

    if account2 and account2.id:
        ins, skip = backfill_account(
            session, account2.id, PENSION_2_BALANCES,
            f"Migdal Pension 2 ({PENSION_2_ACCOUNT_NUMBER})", apply,
        )
        total_inserted += ins
        total_skipped += skip
    elif not apply:
        print(f"\n── Migdal Pension 2 ({PENSION_2_ACCOUNT_NUMBER}) ──")
        for date_str, amount in PENSION_2_BALANCES:
            print(f"  WOULD INSERT {date_str} → ₪{amount:,.0f}")
        total_inserted += len(PENSION_2_BALANCES)

    if apply:
        session.commit()
        print(f"\nDone: {total_inserted} inserted, {total_skipped} skipped")
    else:
        print(f"\nDry run: {total_inserted} would be inserted, {total_skipped} skipped")
        print("Run with --apply to insert")

    session.close()


if __name__ == "__main__":
    main()
