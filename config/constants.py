"""
Application constants and enums.
Eliminates magic strings and provides type safety.
"""


class AccountType:
    """Account type constants"""
    BROKER = "broker"
    PENSION = "pension"
    CREDIT_CARD = "credit_card"
    SAVINGS = "savings"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.BROKER, cls.PENSION, cls.CREDIT_CARD, cls.SAVINGS]


class Institution:
    """Financial institution constants"""
    # Brokers
    EXCELLENCE = "excellence"
    MEITAV = "meitav"

    # Pension Funds
    MIGDAL = "migdal"
    PHOENIX = "phoenix"

    # Credit Cards
    CAL = "cal"
    MAX = "max"
    ISRACARD = "isracard"

    @classmethod
    def brokers(cls) -> list[str]:
        return [cls.EXCELLENCE, cls.MEITAV]

    @classmethod
    def pensions(cls) -> list[str]:
        return [cls.MIGDAL, cls.PHOENIX]

    @classmethod
    def credit_cards(cls) -> list[str]:
        return [cls.CAL, cls.MAX, cls.ISRACARD]

    @classmethod
    def all(cls) -> list[str]:
        return cls.brokers() + cls.pensions() + cls.credit_cards()


class SyncType:
    """Sync operation type constants"""
    ALL = "all"
    BROKER = "broker"
    PENSION = "pension"
    CREDIT_CARD = "credit_card"


class SyncStatus:
    """Sync operation status constants"""
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class TransactionStatus:
    """Transaction status constants"""
    PENDING = "pending"
    COMPLETED = "completed"


class Currency:
    """Currency constants"""
    ILS = "ILS"
    USD = "USD"
    EUR = "EUR"


class UnifiedCategory:
    """Standard unified category names for cross-provider normalization"""
    GROCERIES = "groceries"
    RESTAURANTS = "restaurants"
    FUEL = "fuel"
    TRANSPORTATION = "transportation"
    UTILITIES = "utilities"
    HOME = "home"
    HEALTHCARE = "healthcare"
    BEAUTY = "beauty"
    SHOPPING = "shopping"
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    CHILDREN = "children"
    INSURANCE = "insurance"
    FINANCE = "finance"
    FEES = "fees"
    ENTERTAINMENT = "entertainment"
    TRAVEL = "travel"
    EVENTS = "events"
    SUBSCRIPTIONS = "subscriptions"
    EDUCATION = "education"
    DONATIONS = "donations"
    GIFTS = "gifts"
    SERVICES = "services"
    OTHER = "other"

    @classmethod
    def all(cls) -> list[str]:
        """Get all standard unified category names"""
        return [v for k, v in vars(cls).items()
                if not k.startswith('_') and isinstance(v, str) and k.isupper()]