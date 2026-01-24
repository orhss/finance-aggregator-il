"""
Category service for managing category mappings and normalization.

Handles mapping provider-specific categories (CAL, Max, Isracard) to unified categories.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from db.models import CategoryMapping, MerchantMapping, Transaction, Account
from db.database import get_db
from config.constants import Institution

logger = logging.getLogger(__name__)


class CategoryService:
    """
    Service for managing category mappings and normalization.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize category service.

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

    # ==================== Core Normalization ====================

    def normalize_category(self, provider: str, raw_category: Optional[str]) -> Optional[str]:
        """
        Lookup unified category from mapping.

        Args:
            provider: Provider name (cal, max, isracard)
            raw_category: Original category from provider

        Returns:
            Unified category name or None if not mapped
        """
        if not raw_category:
            return None

        mapping = self.session.query(CategoryMapping).filter(
            CategoryMapping.provider == provider.lower(),
            CategoryMapping.raw_category == raw_category
        ).first()

        return mapping.unified_category if mapping else None

    def normalize_category_cached(self, provider: str, raw_category: Optional[str], cache: Dict) -> Optional[str]:
        """
        Lookup unified category with caching for batch operations.

        Args:
            provider: Provider name
            raw_category: Original category from provider
            cache: Dict to store lookups {(provider, raw): unified}

        Returns:
            Unified category name or None if not mapped
        """
        if not raw_category:
            return None

        key = (provider.lower(), raw_category)
        if key not in cache:
            cache[key] = self.normalize_category(provider, raw_category)
        return cache[key]

    # ==================== Mapping CRUD ====================

    def add_mapping(
        self,
        provider: str,
        raw_category: str,
        unified_category: str
    ) -> CategoryMapping:
        """
        Add or update a category mapping.

        Args:
            provider: Provider name (cal, max, isracard)
            raw_category: Original category from provider
            unified_category: Normalized category name

        Returns:
            CategoryMapping object
        """
        provider = provider.lower()
        mapping = self.session.query(CategoryMapping).filter(
            CategoryMapping.provider == provider,
            CategoryMapping.raw_category == raw_category
        ).first()

        if mapping:
            mapping.unified_category = unified_category
            logger.info(f"Updated mapping: {provider}/{raw_category} -> {unified_category}")
        else:
            mapping = CategoryMapping(
                provider=provider,
                raw_category=raw_category,
                unified_category=unified_category
            )
            self.session.add(mapping)
            logger.info(f"Created mapping: {provider}/{raw_category} -> {unified_category}")

        self.session.commit()
        return mapping

    def remove_mapping(self, provider: str, raw_category: str) -> bool:
        """
        Remove a category mapping.

        Args:
            provider: Provider name
            raw_category: Original category from provider

        Returns:
            True if deleted, False if not found
        """
        mapping = self.session.query(CategoryMapping).filter(
            CategoryMapping.provider == provider.lower(),
            CategoryMapping.raw_category == raw_category
        ).first()

        if not mapping:
            return False

        self.session.delete(mapping)
        self.session.commit()
        logger.info(f"Removed mapping: {provider}/{raw_category}")
        return True

    def get_all_mappings(self, provider: Optional[str] = None) -> List[CategoryMapping]:
        """
        Get all mappings, optionally filtered by provider.

        Args:
            provider: Optional provider filter

        Returns:
            List of CategoryMapping objects
        """
        query = self.session.query(CategoryMapping)
        if provider:
            query = query.filter(CategoryMapping.provider == provider.lower())
        return query.order_by(CategoryMapping.provider, CategoryMapping.raw_category).all()

    def get_mapping(self, provider: str, raw_category: str) -> Optional[CategoryMapping]:
        """
        Get a specific mapping.

        Args:
            provider: Provider name
            raw_category: Original category from provider

        Returns:
            CategoryMapping or None
        """
        return self.session.query(CategoryMapping).filter(
            CategoryMapping.provider == provider.lower(),
            CategoryMapping.raw_category == raw_category
        ).first()

    # ==================== Unmapped Detection ====================

    def get_unmapped_categories(self, provider: Optional[str] = None, max_samples: int = 4) -> List[Dict[str, Any]]:
        """
        Get all (provider, raw_category) pairs that have no mapping.

        Args:
            provider: Optional filter by provider
            max_samples: Maximum number of sample merchants to return per category

        Returns:
            List of dicts: [{provider, raw_category, count, sample_merchants}, ...]
        """
        # Subquery for mapped categories
        mapped_subq = self.session.query(
            CategoryMapping.provider,
            CategoryMapping.raw_category
        ).subquery()

        # First, get the grouped stats
        query = self.session.query(
            Account.institution.label('provider'),
            Transaction.raw_category,
            func.count(Transaction.id).label('count')
        ).join(
            Account, Transaction.account_id == Account.id
        ).outerjoin(
            mapped_subq,
            (Account.institution == mapped_subq.c.provider) &
            (Transaction.raw_category == mapped_subq.c.raw_category)
        ).filter(
            Transaction.raw_category.isnot(None),
            Transaction.raw_category != '',
            mapped_subq.c.raw_category.is_(None)  # Not mapped
        ).group_by(
            Account.institution,
            Transaction.raw_category
        ).order_by(
            func.count(Transaction.id).desc()
        )

        if provider:
            query = query.filter(Account.institution == provider.lower())

        grouped_results = query.all()

        # Now fetch sample merchants for each group
        results = []
        for r in grouped_results:
            # Get distinct sample descriptions for this provider/category
            samples_query = self.session.query(
                distinct(Transaction.description)
            ).join(
                Account, Transaction.account_id == Account.id
            ).filter(
                Account.institution == r.provider,
                Transaction.raw_category == r.raw_category
            ).limit(max_samples)

            sample_merchants = [s[0][:50] if s[0] else None for s in samples_query.all()]
            sample_merchants = [s for s in sample_merchants if s]

            results.append({
                'provider': r.provider,
                'raw_category': r.raw_category,
                'count': r.count,
                'sample_merchants': sample_merchants,
                # Keep backward compatibility
                'sample_merchant': sample_merchants[0] if sample_merchants else None
            })

        return results

    def get_unmapped_count(self, provider: Optional[str] = None) -> int:
        """
        Get count of transactions with unmapped categories.

        Args:
            provider: Optional filter by provider

        Returns:
            Count of transactions
        """
        unmapped = self.get_unmapped_categories(provider)
        return sum(u['count'] for u in unmapped)

    # ==================== Unique Categories ====================

    def get_unique_raw_categories(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get unique raw categories with transaction counts.

        Args:
            provider: Optional filter by provider

        Returns:
            List of dicts: [{provider, raw_category, count, is_mapped, unified_category}, ...]
        """
        query = self.session.query(
            Account.institution.label('provider'),
            Transaction.raw_category,
            func.count(Transaction.id).label('count')
        ).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Transaction.raw_category.isnot(None),
            Transaction.raw_category != ''
        ).group_by(
            Account.institution,
            Transaction.raw_category
        ).order_by(
            Account.institution,
            func.count(Transaction.id).desc()
        )

        if provider:
            query = query.filter(Account.institution == provider.lower())

        results = query.all()

        # Enrich with mapping info
        enriched = []
        for r in results:
            mapping = self.get_mapping(r.provider, r.raw_category)
            enriched.append({
                'provider': r.provider,
                'raw_category': r.raw_category,
                'count': r.count,
                'is_mapped': mapping is not None,
                'unified_category': mapping.unified_category if mapping else None
            })

        return enriched

    def get_unified_categories(self) -> List[str]:
        """
        Get list of all unified category names in use.

        Returns:
            List of unique unified category names
        """
        results = self.session.query(
            distinct(CategoryMapping.unified_category)
        ).order_by(CategoryMapping.unified_category).all()

        return [r[0] for r in results]

    def get_unified_categories_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for unified categories.

        Returns:
            List of dicts: [{unified_category, providers, raw_count, transaction_count}, ...]
        """
        # Get mapping stats
        mapping_stats = self.session.query(
            CategoryMapping.unified_category,
            func.count(CategoryMapping.id).label('raw_count'),
            func.group_concat(distinct(CategoryMapping.provider)).label('providers')
        ).group_by(
            CategoryMapping.unified_category
        ).all()

        results = []
        for stat in mapping_stats:
            # Count transactions using this unified category
            txn_count = self.session.query(func.count(Transaction.id)).filter(
                Transaction.category == stat.unified_category
            ).scalar()

            results.append({
                'unified_category': stat.unified_category,
                'providers': stat.providers.split(',') if stat.providers else [],
                'raw_count': stat.raw_count,
                'transaction_count': txn_count or 0
            })

        return sorted(results, key=lambda x: x['transaction_count'], reverse=True)

    # ==================== Bulk Operations ====================

    def apply_mappings_to_transactions(self, provider: Optional[str] = None) -> Dict[str, int]:
        """
        Apply mappings to existing transactions.

        Args:
            provider: Optional filter by provider

        Returns:
            Dict with counts: {provider: updated_count, ...}
        """
        results = {}

        # Get all mappings
        mappings = self.get_all_mappings(provider)

        # Group by provider
        by_provider = {}
        for m in mappings:
            if m.provider not in by_provider:
                by_provider[m.provider] = {}
            by_provider[m.provider][m.raw_category] = m.unified_category

        # Apply to each provider
        for prov, mapping_dict in by_provider.items():
            # Get accounts for this provider
            accounts = self.session.query(Account).filter(
                Account.institution == prov
            ).all()
            account_ids = [a.id for a in accounts]

            if not account_ids:
                continue

            updated = 0
            for raw_cat, unified_cat in mapping_dict.items():
                # Update transactions with this raw_category
                count = self.session.query(Transaction).filter(
                    Transaction.account_id.in_(account_ids),
                    Transaction.raw_category == raw_cat,
                    Transaction.category != unified_cat  # Only update if different
                ).update(
                    {Transaction.category: unified_cat},
                    synchronize_session=False
                )
                updated += count

            results[prov] = updated

        self.session.commit()
        total = sum(results.values())
        logger.info(f"Applied mappings to {total} transactions: {results}")
        return results

    def clear_normalized_categories(self, provider: Optional[str] = None) -> int:
        """
        Clear normalized category values (set category to NULL).
        Useful for re-applying mappings from scratch.

        Args:
            provider: Optional filter by provider

        Returns:
            Count of transactions updated
        """
        query = self.session.query(Transaction).filter(
            Transaction.category.isnot(None)
        )

        if provider:
            accounts = self.session.query(Account).filter(
                Account.institution == provider.lower()
            ).all()
            account_ids = [a.id for a in accounts]
            query = query.filter(Transaction.account_id.in_(account_ids))

        count = query.update({Transaction.category: None}, synchronize_session=False)
        self.session.commit()
        logger.info(f"Cleared normalized category for {count} transactions")
        return count

    # ==================== Unified Category Management ====================

    def rename_unified_category(self, old_name: str, new_name: str) -> int:
        """
        Rename a unified category across all mappings.

        Args:
            old_name: Current unified category name
            new_name: New unified category name

        Returns:
            Count of mappings updated
        """
        count = self.session.query(CategoryMapping).filter(
            CategoryMapping.unified_category == old_name
        ).update(
            {CategoryMapping.unified_category: new_name},
            synchronize_session=False
        )

        self.session.commit()
        logger.info(f"Renamed unified category '{old_name}' to '{new_name}' ({count} mappings)")
        return count

    def merge_unified_categories(self, sources: List[str], target: str) -> int:
        """
        Merge multiple unified categories into one.

        Args:
            sources: List of unified category names to merge
            target: Target unified category name

        Returns:
            Count of mappings updated
        """
        count = self.session.query(CategoryMapping).filter(
            CategoryMapping.unified_category.in_(sources)
        ).update(
            {CategoryMapping.unified_category: target},
            synchronize_session=False
        )

        self.session.commit()
        logger.info(f"Merged {sources} into '{target}' ({count} mappings)")
        return count

    # ==================== Analysis ====================

    def analyze_categories(self) -> Dict[str, Any]:
        """
        Analyze category coverage across providers.

        Returns:
            Dict with analysis: {
                providers: [{name, unique_categories, transactions, mapped_pct}, ...],
                totals: {unique_categories, transactions, mapped_pct}
            }
        """
        providers = []

        for institution in Institution.credit_cards():
            # Get accounts for this institution
            accounts = self.session.query(Account).filter(
                Account.institution == institution
            ).all()
            account_ids = [a.id for a in accounts]

            if not account_ids:
                continue

            # Count unique raw categories
            unique_count = self.session.query(
                func.count(distinct(Transaction.raw_category))
            ).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.raw_category.isnot(None)
            ).scalar()

            # Count total transactions
            total_txns = self.session.query(func.count(Transaction.id)).filter(
                Transaction.account_id.in_(account_ids)
            ).scalar()

            # Count mapped transactions (have normalized category)
            mapped_txns = self.session.query(func.count(Transaction.id)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.category.isnot(None)
            ).scalar()

            providers.append({
                'name': institution,
                'unique_categories': unique_count or 0,
                'transactions': total_txns or 0,
                'mapped_transactions': mapped_txns or 0,
                'mapped_pct': round(100 * mapped_txns / total_txns, 1) if total_txns else 0
            })

        # Calculate totals
        total_unique = sum(p['unique_categories'] for p in providers)
        total_txns = sum(p['transactions'] for p in providers)
        total_mapped = sum(p['mapped_transactions'] for p in providers)

        return {
            'providers': providers,
            'totals': {
                'unique_categories': total_unique,
                'transactions': total_txns,
                'mapped_transactions': total_mapped,
                'mapped_pct': round(100 * total_mapped / total_txns, 1) if total_txns else 0
            }
        }

    # ==================== Import/Export ====================

    def export_mappings(self) -> List[Dict[str, str]]:
        """
        Export all mappings for backup/sharing.

        Returns:
            List of dicts: [{provider, raw_category, unified_category}, ...]
        """
        mappings = self.get_all_mappings()
        return [
            {
                'provider': m.provider,
                'raw_category': m.raw_category,
                'unified_category': m.unified_category
            }
            for m in mappings
        ]

    def import_mappings(self, mappings: List[Dict[str, str]], overwrite: bool = False) -> Dict[str, int]:
        """
        Import mappings from backup/sharing.

        Args:
            mappings: List of dicts with provider, raw_category, unified_category
            overwrite: If True, overwrite existing mappings

        Returns:
            Dict with counts: {added, updated, skipped}
        """
        results = {'added': 0, 'updated': 0, 'skipped': 0}

        for m in mappings:
            existing = self.get_mapping(m['provider'], m['raw_category'])

            if existing:
                if overwrite:
                    existing.unified_category = m['unified_category']
                    results['updated'] += 1
                else:
                    results['skipped'] += 1
            else:
                self.session.add(CategoryMapping(
                    provider=m['provider'].lower(),
                    raw_category=m['raw_category'],
                    unified_category=m['unified_category']
                ))
                results['added'] += 1

        self.session.commit()
        logger.info(f"Imported mappings: {results}")
        return results

    # ==================== Uncategorized Merchant Grouping ====================

    def extract_merchant_pattern(self, description: str) -> str:
        """
        Extract merchant name pattern from transaction description.

        Heuristics:
        - Take first 2-3 significant words
        - Remove common suffixes (location, date, numbers)
        - Handle Hebrew text

        Examples:
        - "WOLT TLV 123456" → "WOLT"
        - "PANGO PARKING TEL AVIV" → "PANGO PARKING"
        - "סופר יודה רמת גן" → "סופר יודה"
        """
        import re

        if not description:
            return ""

        # Normalize whitespace
        text = " ".join(description.split())

        # Remove trailing numbers, dates, and common suffixes
        # Remove patterns like: 123456, 12/34, TLV, ONLINE, etc.
        text = re.sub(r'\s+\d{4,}$', '', text)  # Trailing long numbers
        text = re.sub(r'\s+\d{1,2}/\d{1,2}(/\d{2,4})?$', '', text)  # Dates
        text = re.sub(r'\s+(TLV|TEL AVIV|HAIFA|JERUSALEM|ONLINE|IL|ISR)\s*$', '', text, flags=re.IGNORECASE)

        # Split into words
        words = text.split()

        if not words:
            return description[:30] if description else ""

        # For Hebrew text, take first 2 words
        # For English, take first 1-2 words depending on length
        if any('\u0590' <= c <= '\u05FF' for c in text):
            # Hebrew - take first 2 words
            pattern = " ".join(words[:2])
        else:
            # English - take first word, or first 2 if first is short
            if len(words[0]) <= 3 and len(words) > 1:
                pattern = " ".join(words[:2])
            else:
                pattern = words[0]

        return pattern.strip()

    def get_uncategorized_by_merchant(
        self,
        min_transactions: int = 1,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Group transactions without unified category by merchant pattern.

        Finds transactions where:
        - category (unified) is NULL, AND
        - raw_category is NULL or empty (nothing to map from provider)

        These are transactions that need a unified category assigned via
        merchant pattern matching. user_category is ignored - we want to
        set the baseline unified category regardless.

        Args:
            min_transactions: Minimum transactions to include a merchant group
            provider: Optional filter by provider/institution

        Returns:
            List of dicts: [{
                merchant_pattern: str,
                provider: str,
                count: int,
                total_amount: float,
                transaction_ids: List[int],
                sample_descriptions: List[str]
            }, ...]
        """
        # Query transactions without unified category and no raw_category to map from
        query = self.session.query(Transaction, Account.institution).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Transaction.category.is_(None),
            (Transaction.raw_category.is_(None) | (Transaction.raw_category == ''))
        )

        if provider:
            query = query.filter(Account.institution == provider.lower())

        transactions = query.all()

        # Group by merchant pattern
        merchant_groups: Dict[str, Dict] = {}

        for txn, institution in transactions:
            pattern = self.extract_merchant_pattern(txn.description)
            key = f"{institution}:{pattern}"

            if key not in merchant_groups:
                merchant_groups[key] = {
                    'merchant_pattern': pattern,
                    'provider': institution,
                    'count': 0,
                    'total_amount': 0.0,
                    'transaction_ids': [],
                    'sample_descriptions': []
                }

            group = merchant_groups[key]
            group['count'] += 1
            group['total_amount'] += abs(txn.original_amount or txn.charged_amount or 0)
            group['transaction_ids'].append(txn.id)

            if len(group['sample_descriptions']) < 3:
                group['sample_descriptions'].append(txn.description[:50])

        # Filter by min_transactions and sort by count
        result = [
            g for g in merchant_groups.values()
            if g['count'] >= min_transactions
        ]
        result.sort(key=lambda x: x['count'], reverse=True)

        return result

    def bulk_set_category(
        self,
        transaction_ids: List[int],
        category: str
    ) -> int:
        """
        Set unified category on multiple transactions.

        Use this for merchant-pattern based categorization (same as provider mapping).
        For user overrides, set user_category directly on the transaction.

        Args:
            transaction_ids: List of transaction IDs to update
            category: Unified category name to set

        Returns:
            Count of transactions updated
        """
        if not transaction_ids:
            return 0

        count = self.session.query(Transaction).filter(
            Transaction.id.in_(transaction_ids)
        ).update(
            {Transaction.category: category},
            synchronize_session=False
        )

        self.session.commit()
        logger.info(f"Set category='{category}' on {count} transactions")
        return count

    def get_total_transaction_count(self) -> int:
        """Get total count of all transactions (for display purposes)."""
        return self.session.query(func.count(Transaction.id)).scalar() or 0

    def get_transactions_with_provider_category_count(self) -> int:
        """Get count of transactions that have a raw_category from provider."""
        return self.session.query(func.count(Transaction.id)).filter(
            Transaction.raw_category.isnot(None),
            Transaction.raw_category != ''
        ).scalar() or 0

    def get_category_coverage_stats(self) -> Dict[str, int]:
        """
        Get comprehensive category coverage statistics.

        Returns:
            {
                'total': int,
                'with_unified_category': int,  # category field is set
                'with_provider_category': int,  # raw_category is set
                'without_provider_category': int,  # raw_category is NULL/empty
                'needs_attention': int,  # no unified category (category is NULL)
            }
        """
        total = self.session.query(func.count(Transaction.id)).scalar() or 0

        with_unified = self.session.query(func.count(Transaction.id)).filter(
            Transaction.category.isnot(None)
        ).scalar() or 0

        with_provider = self.session.query(func.count(Transaction.id)).filter(
            Transaction.raw_category.isnot(None),
            Transaction.raw_category != ''
        ).scalar() or 0

        without_provider = total - with_provider

        needs_attention = self.session.query(func.count(Transaction.id)).filter(
            Transaction.category.is_(None)
        ).scalar() or 0

        return {
            'total': total,
            'with_unified_category': with_unified,
            'with_provider_category': with_provider,
            'without_provider_category': without_provider,
            'needs_attention': needs_attention,
        }

    # ==================== Merchant Mapping CRUD ====================

    def add_merchant_mapping(
        self,
        pattern: str,
        category: str,
        provider: Optional[str] = None,
        match_type: str = 'startswith'
    ) -> MerchantMapping:
        """
        Add or update a merchant mapping.

        Args:
            pattern: Merchant pattern to match (from transaction description)
            category: Unified category to assign
            provider: Optional provider to limit mapping to (e.g., 'isracard')
            match_type: How to match - 'startswith', 'contains', 'exact'

        Returns:
            MerchantMapping object
        """
        provider_lower = provider.lower() if provider else None

        mapping = self.session.query(MerchantMapping).filter(
            MerchantMapping.pattern == pattern,
            MerchantMapping.provider == provider_lower
        ).first()

        if mapping:
            mapping.category = category
            mapping.match_type = match_type
            logger.info(f"Updated merchant mapping: {pattern} -> {category}")
        else:
            mapping = MerchantMapping(
                pattern=pattern,
                category=category,
                provider=provider_lower,
                match_type=match_type
            )
            self.session.add(mapping)
            logger.info(f"Created merchant mapping: {pattern} -> {category}")

        self.session.commit()
        return mapping

    def remove_merchant_mapping(self, pattern: str, provider: Optional[str] = None) -> bool:
        """
        Remove a merchant mapping.

        Args:
            pattern: Merchant pattern
            provider: Optional provider filter

        Returns:
            True if deleted, False if not found
        """
        provider_lower = provider.lower() if provider else None

        mapping = self.session.query(MerchantMapping).filter(
            MerchantMapping.pattern == pattern,
            MerchantMapping.provider == provider_lower
        ).first()

        if not mapping:
            return False

        self.session.delete(mapping)
        self.session.commit()
        logger.info(f"Removed merchant mapping: {pattern}")
        return True

    def get_all_merchant_mappings(self, provider: Optional[str] = None) -> List[MerchantMapping]:
        """
        Get all merchant mappings, optionally filtered by provider.

        Args:
            provider: Optional provider filter

        Returns:
            List of MerchantMapping objects
        """
        query = self.session.query(MerchantMapping)
        if provider:
            query = query.filter(
                (MerchantMapping.provider == provider.lower()) |
                (MerchantMapping.provider.is_(None))
            )
        return query.order_by(MerchantMapping.pattern).all()

    def get_merchant_mapping(self, pattern: str, provider: Optional[str] = None) -> Optional[MerchantMapping]:
        """
        Get a specific merchant mapping.

        Args:
            pattern: Merchant pattern
            provider: Optional provider filter

        Returns:
            MerchantMapping or None
        """
        provider_lower = provider.lower() if provider else None
        return self.session.query(MerchantMapping).filter(
            MerchantMapping.pattern == pattern,
            MerchantMapping.provider == provider_lower
        ).first()

    # ==================== Merchant Mapping Application ====================

    def normalize_by_merchant(self, description: str, provider: Optional[str] = None) -> Optional[str]:
        """
        Find matching merchant mapping for a transaction description.

        Checks mappings in order of specificity:
        1. Provider-specific mappings (if provider given)
        2. Global mappings (provider is NULL)

        Args:
            description: Transaction description
            provider: Optional provider name

        Returns:
            Unified category name or None if no match
        """
        if not description:
            return None

        # Get applicable mappings (provider-specific first, then global)
        mappings = []
        if provider:
            # Provider-specific mappings
            mappings.extend(
                self.session.query(MerchantMapping)
                .filter(MerchantMapping.provider == provider.lower())
                .all()
            )
        # Global mappings
        mappings.extend(
            self.session.query(MerchantMapping)
            .filter(MerchantMapping.provider.is_(None))
            .all()
        )

        # Find first matching mapping
        for mapping in mappings:
            if mapping.matches(description):
                return mapping.category

        return None

    def bulk_set_category_with_mapping(
        self,
        merchant_pattern: str,
        category: str,
        transaction_ids: List[int],
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set category on transactions AND save the merchant mapping for future use.

        This is the main method to use when categorizing by merchant pattern.
        It both updates existing transactions and creates a mapping for future syncs.

        Args:
            merchant_pattern: Pattern extracted from transaction descriptions
            category: Unified category to assign
            transaction_ids: Transaction IDs to update
            provider: Optional provider to scope the mapping

        Returns:
            {transactions_updated: int, mapping_created: bool}
        """
        # Update transactions
        txn_count = self.bulk_set_category(transaction_ids, category)

        # Save merchant mapping for future transactions
        existing = self.get_merchant_mapping(merchant_pattern, provider)
        mapping_created = existing is None

        self.add_merchant_mapping(merchant_pattern, category, provider)

        logger.info(f"Bulk categorized {txn_count} transactions as '{category}' and saved mapping for '{merchant_pattern}'")

        return {
            'transactions_updated': txn_count,
            'mapping_created': mapping_created
        }

    def apply_merchant_mappings_to_transaction(
        self,
        transaction: Transaction,
        provider: Optional[str] = None
    ) -> bool:
        """
        Apply merchant mappings to a single transaction.

        Called during sync for transactions without raw_category.

        Args:
            transaction: Transaction to categorize
            provider: Provider name (for provider-specific mappings)

        Returns:
            True if category was set, False otherwise
        """
        if transaction.category:
            # Already has a category
            return False

        category = self.normalize_by_merchant(transaction.description, provider)
        if category:
            transaction.category = category
            return True

        return False

    def apply_merchant_mappings_batch(self, provider: Optional[str] = None) -> int:
        """
        Apply merchant mappings to all uncategorized transactions.

        Args:
            provider: Optional provider filter

        Returns:
            Count of transactions updated
        """
        # Get transactions without category and without raw_category
        query = self.session.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Transaction.category.is_(None),
            (Transaction.raw_category.is_(None) | (Transaction.raw_category == ''))
        )

        if provider:
            query = query.filter(Account.institution == provider.lower())

        transactions = query.all()
        updated = 0

        for txn in transactions:
            # Get provider from account
            account = self.session.query(Account).get(txn.account_id)
            if self.apply_merchant_mappings_to_transaction(txn, account.institution if account else None):
                updated += 1

        self.session.commit()
        logger.info(f"Applied merchant mappings to {updated} transactions")
        return updated