"""
Style Preview Page - Visual mockups of 3 different UI design approaches.

This temporary page allows comparison of:
1. Hybrid Material + Glassmorphism (recommended)
2. Full Glassmorphism
3. Pure Material Design

After selection, delete this file and implement the chosen design.
"""

import streamlit as st
from streamlit.components.v1 import html

st.set_page_config(
    page_title="Style Preview",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# SAMPLE DATA (Hardcoded for preview purposes)
# ============================================================================

SAMPLE_DATA = {
    "net_worth": "₪127,450",
    "last_sync": "2 hours ago",
    "monthly_spending": "₪8,234",
    "pending_count": 3,
    "pending_amount": "₪1,240",
    "account_count": 5,
    "transaction_count": "1,247",
    "budget_spent": 8234,
    "budget_total": 12000,
    "budget_percent": 69,
    "budget_remaining": "₪3,766",
    "insight": "You're 15% under budget compared to last month. Keep it up!",
    "transactions": [
        {"date": "Today", "icon": "🛒", "merchant": "Shufersal Deal", "category": "groceries", "amount": "-₪287"},
        {"date": "Today", "icon": "⛽", "merchant": "Sonol Gas Station", "category": "fuel", "amount": "-₪350"},
        {"date": "Yesterday", "icon": "🍕", "merchant": "Domino's Pizza", "category": "restaurants", "amount": "-₪89"},
        {"date": "Yesterday", "icon": "📱", "merchant": "Partner Cellular", "category": "subscriptions", "amount": "-₪99"},
        {"date": "Jan 26", "icon": "🎬", "merchant": "Netflix", "category": "subscriptions", "amount": "-₪50"},
    ],
    "accounts": [
        {"name": "CAL", "subtitle": "2 cards", "balance": "₪-4,230"},
        {"name": "MAX", "subtitle": "1 card", "balance": "₪-2,180"},
        {"name": "EXCELLENCE", "subtitle": "1 account", "balance": "₪133,860"},
    ],
    "alerts": [
        {"icon": "⚠️", "message": "2 accounts haven't synced in 7+ days", "type": "sync"},
        {"icon": "🏷️", "message": "12 transactions need categorization", "type": "category"},
    ],
}

# ============================================================================
# STYLE 1: HYBRID MATERIAL + GLASSMORPHISM
# ============================================================================

HYBRID_LIGHT_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #1f2937;
            padding: 1.5rem;
            line-height: 1.5;
        }}

        /* Hero Card - Gradient with subtle glass overlay */
        .hero-card {{
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border-radius: 24px;
            padding: 2rem 2.5rem;
            color: white;
            position: relative;
            overflow: hidden;
            margin-bottom: 1.5rem;
        }}
        .hero-card::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 60%;
            height: 150%;
            background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
            pointer-events: none;
        }}
        .hero-label {{
            font-size: 0.9rem;
            opacity: 0.9;
            font-weight: 500;
            margin-bottom: 0.25rem;
        }}
        .hero-amount {{
            font-size: 3rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 0.5rem;
        }}
        .hero-sync {{
            font-size: 0.85rem;
            opacity: 0.8;
        }}

        /* Metrics Row */
        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            background: white;
            border-radius: 16px;
            padding: 1.25rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04);
            border: 1px solid rgba(0,0,0,0.05);
            text-align: center;
        }}
        .metric-value {{
            font-size: 1.5rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.25rem;
        }}
        .metric-label {{
            font-size: 0.8rem;
            color: #6b7280;
            font-weight: 500;
        }}
        .metric-sublabel {{
            font-size: 0.7rem;
            color: #9ca3af;
            margin-top: 0.25rem;
        }}

        /* Budget Progress */
        .budget-card {{
            background: white;
            border-radius: 16px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04);
            border: 1px solid rgba(0,0,0,0.05);
            margin-bottom: 1.5rem;
        }}
        .budget-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .budget-title {{
            font-weight: 600;
            color: #1f2937;
        }}
        .budget-remaining {{
            font-size: 0.9rem;
            color: #10b981;
            font-weight: 500;
        }}
        .budget-bar-bg {{
            height: 10px;
            background: #e5e7eb;
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }}
        .budget-bar {{
            height: 100%;
            background: linear-gradient(90deg, #10b981, #34d399);
            border-radius: 999px;
            width: 69%;
            transition: width 0.3s ease;
        }}
        .budget-details {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #6b7280;
        }}

        /* Insight Banner */
        .insight-banner {{
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .insight-icon {{
            font-size: 1.25rem;
        }}
        .insight-message {{
            color: #065f46;
            font-weight: 500;
            font-size: 0.9rem;
        }}

        /* Alerts */
        .alerts-section {{
            margin-bottom: 1.5rem;
        }}
        .section-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            color: #374151;
        }}
        .alert-card {{
            background: white;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .alert-card.sync {{
            border-left: 4px solid #f59e0b;
        }}
        .alert-card.category {{
            border-left: 4px solid #6366f1;
        }}
        .alert-message {{
            flex: 1;
            font-size: 0.9rem;
            color: #374151;
        }}
        .alert-action {{
            padding: 0.5rem 1rem;
            background: #f3f4f6;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 500;
            color: #6b7280;
            border: none;
            cursor: pointer;
        }}
        .alert-action:hover {{
            background: #e5e7eb;
        }}

        /* Two Column Layout */
        .two-columns {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 1.5rem;
        }}

        /* Transaction Card */
        .card {{
            background: white;
            border-radius: 16px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04);
            border: 1px solid rgba(0,0,0,0.05);
        }}
        .card-header {{
            font-size: 1rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #f3f4f6;
        }}
        .date-header {{
            font-size: 0.7rem;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0.75rem 0 0.5rem 0;
        }}
        .date-header:first-of-type {{
            margin-top: 0;
        }}
        .txn-item {{
            display: flex;
            align-items: center;
            padding: 0.6rem 0;
            border-bottom: 1px solid #f9fafb;
        }}
        .txn-item:last-child {{
            border-bottom: none;
        }}
        .txn-icon {{
            font-size: 1.2rem;
            width: 32px;
            text-align: center;
        }}
        .txn-details {{
            flex: 1;
            margin-left: 0.5rem;
        }}
        .txn-merchant {{
            font-weight: 500;
            color: #1f2937;
            font-size: 0.9rem;
        }}
        .txn-category {{
            display: inline-block;
            font-size: 0.65rem;
            padding: 0.1rem 0.5rem;
            border-radius: 999px;
            background: #eef2ff;
            color: #6366f1;
            margin-top: 0.15rem;
        }}
        .txn-amount {{
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-weight: 500;
            font-size: 0.9rem;
            color: #dc2626;
        }}

        /* Account Item */
        .account-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            background: #fafafa;
            border-radius: 12px;
            margin-bottom: 0.5rem;
        }}
        .account-item:last-child {{
            margin-bottom: 0;
        }}
        .account-name {{
            font-weight: 600;
            color: #1f2937;
            font-size: 0.95rem;
        }}
        .account-subtitle {{
            font-size: 0.8rem;
            color: #6b7280;
        }}
        .account-balance {{
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-weight: 500;
            color: #1f2937;
        }}
        .account-balance.negative {{
            color: #dc2626;
        }}

        /* View All Button */
        .view-all {{
            display: block;
            width: 100%;
            margin-top: 1rem;
            padding: 0.75rem;
            background: #f3f4f6;
            border: none;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 500;
            color: #6b7280;
            cursor: pointer;
            text-align: center;
        }}
        .view-all:hover {{
            background: #e5e7eb;
            color: #374151;
        }}
    </style>
</head>
<body>
    <!-- Hero Card -->
    <div class="hero-card">
        <div class="hero-label">Net Worth</div>
        <div class="hero-amount">{SAMPLE_DATA['net_worth']}</div>
        <div class="hero-sync">Last synced {SAMPLE_DATA['last_sync']}</div>
    </div>

    <!-- Metrics Row -->
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['monthly_spending']}</div>
            <div class="metric-label">This Month</div>
            <div class="metric-sublabel">spent</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['pending_count']}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-sublabel">{SAMPLE_DATA['pending_amount']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['account_count']}</div>
            <div class="metric-label">Accounts</div>
            <div class="metric-sublabel">{SAMPLE_DATA['transaction_count']} txns</div>
        </div>
    </div>

    <!-- Budget Progress -->
    <div class="budget-card">
        <div class="budget-header">
            <span class="budget-title">Monthly Budget</span>
            <span class="budget-remaining">{SAMPLE_DATA['budget_remaining']} remaining</span>
        </div>
        <div class="budget-bar-bg">
            <div class="budget-bar"></div>
        </div>
        <div class="budget-details">
            <span>₪{SAMPLE_DATA['budget_spent']:,} of ₪{SAMPLE_DATA['budget_total']:,}</span>
            <span>{SAMPLE_DATA['budget_percent']}%</span>
        </div>
    </div>

    <!-- Insight Banner -->
    <div class="insight-banner">
        <span class="insight-icon">📈</span>
        <span class="insight-message">{SAMPLE_DATA['insight']}</span>
    </div>

    <!-- Alerts -->
    <div class="alerts-section">
        <div class="section-title">Needs Attention</div>
        <div class="alert-card sync">
            <span>⚠️</span>
            <span class="alert-message">{SAMPLE_DATA['alerts'][0]['message']}</span>
            <button class="alert-action">Sync Now</button>
        </div>
        <div class="alert-card category">
            <span>🏷️</span>
            <span class="alert-message">{SAMPLE_DATA['alerts'][1]['message']}</span>
            <button class="alert-action">Review</button>
        </div>
    </div>

    <!-- Two Column Layout -->
    <div class="two-columns">
        <!-- Recent Activity -->
        <div class="card">
            <div class="card-header">📋 Recent Activity</div>
            <div class="date-header">Today</div>
            <div class="txn-item">
                <span class="txn-icon">🛒</span>
                <div class="txn-details">
                    <div class="txn-merchant">Shufersal Deal</div>
                    <span class="txn-category">groceries</span>
                </div>
                <span class="txn-amount">-₪287</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">⛽</span>
                <div class="txn-details">
                    <div class="txn-merchant">Sonol Gas Station</div>
                    <span class="txn-category">fuel</span>
                </div>
                <span class="txn-amount">-₪350</span>
            </div>
            <div class="date-header">Yesterday</div>
            <div class="txn-item">
                <span class="txn-icon">🍕</span>
                <div class="txn-details">
                    <div class="txn-merchant">Domino's Pizza</div>
                    <span class="txn-category">restaurants</span>
                </div>
                <span class="txn-amount">-₪89</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">📱</span>
                <div class="txn-details">
                    <div class="txn-merchant">Partner Cellular</div>
                    <span class="txn-category">subscriptions</span>
                </div>
                <span class="txn-amount">-₪99</span>
            </div>
            <button class="view-all">View all transactions</button>
        </div>

        <!-- Accounts Summary -->
        <div class="card">
            <div class="card-header">🏦 Accounts</div>
            <div class="account-item">
                <div>
                    <div class="account-name">CAL</div>
                    <div class="account-subtitle">2 cards</div>
                </div>
                <div class="account-balance negative">₪-4,230</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">MAX</div>
                    <div class="account-subtitle">1 card</div>
                </div>
                <div class="account-balance negative">₪-2,180</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">EXCELLENCE</div>
                    <div class="account-subtitle">1 account</div>
                </div>
                <div class="account-balance">₪133,860</div>
            </div>
            <button class="view-all">View all accounts</button>
        </div>
    </div>
</body>
</html>
"""

HYBRID_DARK_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 1.5rem;
            line-height: 1.5;
        }}

        /* Hero Card - Gradient with glass effect */
        .hero-card {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            border-radius: 24px;
            padding: 2rem 2.5rem;
            color: white;
            position: relative;
            overflow: hidden;
            margin-bottom: 1.5rem;
            box-shadow: 0 25px 50px -12px rgba(79, 70, 229, 0.3);
        }}
        .hero-card::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 60%;
            height: 150%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            pointer-events: none;
        }}
        .hero-label {{
            font-size: 0.9rem;
            opacity: 0.85;
            font-weight: 500;
            margin-bottom: 0.25rem;
        }}
        .hero-amount {{
            font-size: 3rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 0.5rem;
        }}
        .hero-sync {{
            font-size: 0.85rem;
            opacity: 0.75;
        }}

        /* Metrics Row */
        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            background: #1e293b;
            border-radius: 16px;
            padding: 1.25rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.05);
            text-align: center;
        }}
        .metric-value {{
            font-size: 1.5rem;
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 0.25rem;
        }}
        .metric-label {{
            font-size: 0.8rem;
            color: #94a3b8;
            font-weight: 500;
        }}
        .metric-sublabel {{
            font-size: 0.7rem;
            color: #64748b;
            margin-top: 0.25rem;
        }}

        /* Budget Progress */
        .budget-card {{
            background: #1e293b;
            border-radius: 16px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.05);
            margin-bottom: 1.5rem;
        }}
        .budget-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .budget-title {{
            font-weight: 600;
            color: #f1f5f9;
        }}
        .budget-remaining {{
            font-size: 0.9rem;
            color: #34d399;
            font-weight: 500;
        }}
        .budget-bar-bg {{
            height: 10px;
            background: #334155;
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }}
        .budget-bar {{
            height: 100%;
            background: linear-gradient(90deg, #10b981, #34d399);
            border-radius: 999px;
            width: 69%;
        }}
        .budget-details {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #94a3b8;
        }}

        /* Insight Banner */
        .insight-banner {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(52, 211, 153, 0.1) 100%);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .insight-icon {{
            font-size: 1.25rem;
        }}
        .insight-message {{
            color: #6ee7b7;
            font-weight: 500;
            font-size: 0.9rem;
        }}

        /* Alerts */
        .alerts-section {{
            margin-bottom: 1.5rem;
        }}
        .section-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            color: #e2e8f0;
        }}
        .alert-card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .alert-card.sync {{
            border-left: 4px solid #f59e0b;
        }}
        .alert-card.category {{
            border-left: 4px solid #818cf8;
        }}
        .alert-message {{
            flex: 1;
            font-size: 0.9rem;
            color: #e2e8f0;
        }}
        .alert-action {{
            padding: 0.5rem 1rem;
            background: #334155;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 500;
            color: #94a3b8;
            border: none;
            cursor: pointer;
        }}
        .alert-action:hover {{
            background: #475569;
            color: #f1f5f9;
        }}

        /* Two Column Layout */
        .two-columns {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 1.5rem;
        }}

        /* Cards */
        .card {{
            background: #1e293b;
            border-radius: 16px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .card-header {{
            font-size: 1rem;
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #334155;
        }}
        .date-header {{
            font-size: 0.7rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0.75rem 0 0.5rem 0;
        }}
        .date-header:first-of-type {{
            margin-top: 0;
        }}
        .txn-item {{
            display: flex;
            align-items: center;
            padding: 0.6rem 0;
            border-bottom: 1px solid #1e293b;
        }}
        .txn-item:last-child {{
            border-bottom: none;
        }}
        .txn-icon {{
            font-size: 1.2rem;
            width: 32px;
            text-align: center;
        }}
        .txn-details {{
            flex: 1;
            margin-left: 0.5rem;
        }}
        .txn-merchant {{
            font-weight: 500;
            color: #f1f5f9;
            font-size: 0.9rem;
        }}
        .txn-category {{
            display: inline-block;
            font-size: 0.65rem;
            padding: 0.1rem 0.5rem;
            border-radius: 999px;
            background: rgba(129, 140, 248, 0.15);
            color: #a5b4fc;
            margin-top: 0.15rem;
        }}
        .txn-amount {{
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-weight: 500;
            font-size: 0.9rem;
            color: #f87171;
        }}

        /* Account Item */
        .account-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            background: #0f172a;
            border-radius: 12px;
            margin-bottom: 0.5rem;
        }}
        .account-item:last-child {{
            margin-bottom: 0;
        }}
        .account-name {{
            font-weight: 600;
            color: #f1f5f9;
            font-size: 0.95rem;
        }}
        .account-subtitle {{
            font-size: 0.8rem;
            color: #64748b;
        }}
        .account-balance {{
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-weight: 500;
            color: #f1f5f9;
        }}
        .account-balance.negative {{
            color: #f87171;
        }}

        /* View All Button */
        .view-all {{
            display: block;
            width: 100%;
            margin-top: 1rem;
            padding: 0.75rem;
            background: #334155;
            border: none;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 500;
            color: #94a3b8;
            cursor: pointer;
            text-align: center;
        }}
        .view-all:hover {{
            background: #475569;
            color: #f1f5f9;
        }}
    </style>
</head>
<body>
    <!-- Hero Card -->
    <div class="hero-card">
        <div class="hero-label">Net Worth</div>
        <div class="hero-amount">{SAMPLE_DATA['net_worth']}</div>
        <div class="hero-sync">Last synced {SAMPLE_DATA['last_sync']}</div>
    </div>

    <!-- Metrics Row -->
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['monthly_spending']}</div>
            <div class="metric-label">This Month</div>
            <div class="metric-sublabel">spent</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['pending_count']}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-sublabel">{SAMPLE_DATA['pending_amount']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['account_count']}</div>
            <div class="metric-label">Accounts</div>
            <div class="metric-sublabel">{SAMPLE_DATA['transaction_count']} txns</div>
        </div>
    </div>

    <!-- Budget Progress -->
    <div class="budget-card">
        <div class="budget-header">
            <span class="budget-title">Monthly Budget</span>
            <span class="budget-remaining">{SAMPLE_DATA['budget_remaining']} remaining</span>
        </div>
        <div class="budget-bar-bg">
            <div class="budget-bar"></div>
        </div>
        <div class="budget-details">
            <span>₪{SAMPLE_DATA['budget_spent']:,} of ₪{SAMPLE_DATA['budget_total']:,}</span>
            <span>{SAMPLE_DATA['budget_percent']}%</span>
        </div>
    </div>

    <!-- Insight Banner -->
    <div class="insight-banner">
        <span class="insight-icon">📈</span>
        <span class="insight-message">{SAMPLE_DATA['insight']}</span>
    </div>

    <!-- Alerts -->
    <div class="alerts-section">
        <div class="section-title">Needs Attention</div>
        <div class="alert-card sync">
            <span>⚠️</span>
            <span class="alert-message">{SAMPLE_DATA['alerts'][0]['message']}</span>
            <button class="alert-action">Sync Now</button>
        </div>
        <div class="alert-card category">
            <span>🏷️</span>
            <span class="alert-message">{SAMPLE_DATA['alerts'][1]['message']}</span>
            <button class="alert-action">Review</button>
        </div>
    </div>

    <!-- Two Column Layout -->
    <div class="two-columns">
        <!-- Recent Activity -->
        <div class="card">
            <div class="card-header">📋 Recent Activity</div>
            <div class="date-header">Today</div>
            <div class="txn-item">
                <span class="txn-icon">🛒</span>
                <div class="txn-details">
                    <div class="txn-merchant">Shufersal Deal</div>
                    <span class="txn-category">groceries</span>
                </div>
                <span class="txn-amount">-₪287</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">⛽</span>
                <div class="txn-details">
                    <div class="txn-merchant">Sonol Gas Station</div>
                    <span class="txn-category">fuel</span>
                </div>
                <span class="txn-amount">-₪350</span>
            </div>
            <div class="date-header">Yesterday</div>
            <div class="txn-item">
                <span class="txn-icon">🍕</span>
                <div class="txn-details">
                    <div class="txn-merchant">Domino's Pizza</div>
                    <span class="txn-category">restaurants</span>
                </div>
                <span class="txn-amount">-₪89</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">📱</span>
                <div class="txn-details">
                    <div class="txn-merchant">Partner Cellular</div>
                    <span class="txn-category">subscriptions</span>
                </div>
                <span class="txn-amount">-₪99</span>
            </div>
            <button class="view-all">View all transactions</button>
        </div>

        <!-- Accounts Summary -->
        <div class="card">
            <div class="card-header">🏦 Accounts</div>
            <div class="account-item">
                <div>
                    <div class="account-name">CAL</div>
                    <div class="account-subtitle">2 cards</div>
                </div>
                <div class="account-balance negative">₪-4,230</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">MAX</div>
                    <div class="account-subtitle">1 card</div>
                </div>
                <div class="account-balance negative">₪-2,180</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">EXCELLENCE</div>
                    <div class="account-subtitle">1 account</div>
                </div>
                <div class="account-balance">₪133,860</div>
            </div>
            <button class="view-all">View all accounts</button>
        </div>
    </div>
</body>
</html>
"""

# ============================================================================
# STYLE 2: FULL GLASSMORPHISM
# ============================================================================

GLASSMORPHISM_LIGHT_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            min-height: 100%;
            padding: 1.5rem;
            line-height: 1.5;
        }}

        /* Glass Card Base */
        .glass {{
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 24px;
        }}

        /* Hero Card */
        .hero-card {{
            padding: 2rem 2.5rem;
            margin-bottom: 1.5rem;
            color: white;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }}
        .hero-label {{
            font-size: 0.9rem;
            opacity: 0.9;
            font-weight: 500;
            margin-bottom: 0.25rem;
        }}
        .hero-amount {{
            font-size: 3rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 0.5rem;
        }}
        .hero-sync {{
            font-size: 0.85rem;
            opacity: 0.8;
        }}

        /* Metrics Row */
        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            padding: 1.25rem;
            text-align: center;
            color: white;
        }}
        .metric-value {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        .metric-label {{
            font-size: 0.8rem;
            opacity: 0.9;
            font-weight: 500;
        }}
        .metric-sublabel {{
            font-size: 0.7rem;
            opacity: 0.7;
            margin-top: 0.25rem;
        }}

        /* Budget Progress */
        .budget-card {{
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
            color: white;
        }}
        .budget-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .budget-title {{
            font-weight: 600;
        }}
        .budget-remaining {{
            font-size: 0.9rem;
            color: #a7f3d0;
            font-weight: 500;
        }}
        .budget-bar-bg {{
            height: 10px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }}
        .budget-bar {{
            height: 100%;
            background: linear-gradient(90deg, #a7f3d0, #6ee7b7);
            border-radius: 999px;
            width: 69%;
        }}
        .budget-details {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            opacity: 0.8;
        }}

        /* Insight Banner */
        .insight-banner {{
            background: rgba(167, 243, 208, 0.25);
            border: 1px solid rgba(167, 243, 208, 0.4);
            border-radius: 16px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: white;
        }}
        .insight-icon {{
            font-size: 1.25rem;
        }}
        .insight-message {{
            font-weight: 500;
            font-size: 0.9rem;
        }}

        /* Alerts */
        .alerts-section {{
            margin-bottom: 1.5rem;
        }}
        .section-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            color: white;
        }}
        .alert-card {{
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: white;
        }}
        .alert-card.sync {{
            border-left: 4px solid #fbbf24;
        }}
        .alert-card.category {{
            border-left: 4px solid #c4b5fd;
        }}
        .alert-message {{
            flex: 1;
            font-size: 0.9rem;
        }}
        .alert-action {{
            padding: 0.5rem 1rem;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            font-size: 0.8rem;
            font-weight: 500;
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
            cursor: pointer;
        }}
        .alert-action:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}

        /* Two Column Layout */
        .two-columns {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 1.5rem;
        }}

        /* Cards */
        .card {{
            padding: 1.25rem 1.5rem;
            color: white;
        }}
        .card-header {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}
        .date-header {{
            font-size: 0.7rem;
            font-weight: 600;
            opacity: 0.7;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0.75rem 0 0.5rem 0;
        }}
        .date-header:first-of-type {{
            margin-top: 0;
        }}
        .txn-item {{
            display: flex;
            align-items: center;
            padding: 0.6rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .txn-item:last-child {{
            border-bottom: none;
        }}
        .txn-icon {{
            font-size: 1.2rem;
            width: 32px;
            text-align: center;
        }}
        .txn-details {{
            flex: 1;
            margin-left: 0.5rem;
        }}
        .txn-merchant {{
            font-weight: 500;
            font-size: 0.9rem;
        }}
        .txn-category {{
            display: inline-block;
            font-size: 0.65rem;
            padding: 0.1rem 0.5rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.2);
            margin-top: 0.15rem;
        }}
        .txn-amount {{
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-weight: 500;
            font-size: 0.9rem;
            color: #fca5a5;
        }}

        /* Account Item */
        .account-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            margin-bottom: 0.5rem;
        }}
        .account-item:last-child {{
            margin-bottom: 0;
        }}
        .account-name {{
            font-weight: 600;
            font-size: 0.95rem;
        }}
        .account-subtitle {{
            font-size: 0.8rem;
            opacity: 0.7;
        }}
        .account-balance {{
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-weight: 500;
        }}
        .account-balance.negative {{
            color: #fca5a5;
        }}

        /* View All Button */
        .view-all {{
            display: block;
            width: 100%;
            margin-top: 1rem;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 500;
            color: white;
            cursor: pointer;
            text-align: center;
        }}
        .view-all:hover {{
            background: rgba(255, 255, 255, 0.25);
        }}
    </style>
</head>
<body>
    <!-- Hero Card -->
    <div class="hero-card glass">
        <div class="hero-label">Net Worth</div>
        <div class="hero-amount">{SAMPLE_DATA['net_worth']}</div>
        <div class="hero-sync">Last synced {SAMPLE_DATA['last_sync']}</div>
    </div>

    <!-- Metrics Row -->
    <div class="metrics-row">
        <div class="metric-card glass">
            <div class="metric-value">{SAMPLE_DATA['monthly_spending']}</div>
            <div class="metric-label">This Month</div>
            <div class="metric-sublabel">spent</div>
        </div>
        <div class="metric-card glass">
            <div class="metric-value">{SAMPLE_DATA['pending_count']}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-sublabel">{SAMPLE_DATA['pending_amount']}</div>
        </div>
        <div class="metric-card glass">
            <div class="metric-value">{SAMPLE_DATA['account_count']}</div>
            <div class="metric-label">Accounts</div>
            <div class="metric-sublabel">{SAMPLE_DATA['transaction_count']} txns</div>
        </div>
    </div>

    <!-- Budget Progress -->
    <div class="budget-card glass">
        <div class="budget-header">
            <span class="budget-title">Monthly Budget</span>
            <span class="budget-remaining">{SAMPLE_DATA['budget_remaining']} remaining</span>
        </div>
        <div class="budget-bar-bg">
            <div class="budget-bar"></div>
        </div>
        <div class="budget-details">
            <span>₪{SAMPLE_DATA['budget_spent']:,} of ₪{SAMPLE_DATA['budget_total']:,}</span>
            <span>{SAMPLE_DATA['budget_percent']}%</span>
        </div>
    </div>

    <!-- Insight Banner -->
    <div class="insight-banner">
        <span class="insight-icon">📈</span>
        <span class="insight-message">{SAMPLE_DATA['insight']}</span>
    </div>

    <!-- Alerts -->
    <div class="alerts-section">
        <div class="section-title">Needs Attention</div>
        <div class="alert-card sync">
            <span>⚠️</span>
            <span class="alert-message">{SAMPLE_DATA['alerts'][0]['message']}</span>
            <button class="alert-action">Sync Now</button>
        </div>
        <div class="alert-card category">
            <span>🏷️</span>
            <span class="alert-message">{SAMPLE_DATA['alerts'][1]['message']}</span>
            <button class="alert-action">Review</button>
        </div>
    </div>

    <!-- Two Column Layout -->
    <div class="two-columns">
        <!-- Recent Activity -->
        <div class="card glass">
            <div class="card-header">📋 Recent Activity</div>
            <div class="date-header">Today</div>
            <div class="txn-item">
                <span class="txn-icon">🛒</span>
                <div class="txn-details">
                    <div class="txn-merchant">Shufersal Deal</div>
                    <span class="txn-category">groceries</span>
                </div>
                <span class="txn-amount">-₪287</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">⛽</span>
                <div class="txn-details">
                    <div class="txn-merchant">Sonol Gas Station</div>
                    <span class="txn-category">fuel</span>
                </div>
                <span class="txn-amount">-₪350</span>
            </div>
            <div class="date-header">Yesterday</div>
            <div class="txn-item">
                <span class="txn-icon">🍕</span>
                <div class="txn-details">
                    <div class="txn-merchant">Domino's Pizza</div>
                    <span class="txn-category">restaurants</span>
                </div>
                <span class="txn-amount">-₪89</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">📱</span>
                <div class="txn-details">
                    <div class="txn-merchant">Partner Cellular</div>
                    <span class="txn-category">subscriptions</span>
                </div>
                <span class="txn-amount">-₪99</span>
            </div>
            <button class="view-all">View all transactions</button>
        </div>

        <!-- Accounts Summary -->
        <div class="card glass">
            <div class="card-header">🏦 Accounts</div>
            <div class="account-item">
                <div>
                    <div class="account-name">CAL</div>
                    <div class="account-subtitle">2 cards</div>
                </div>
                <div class="account-balance negative">₪-4,230</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">MAX</div>
                    <div class="account-subtitle">1 card</div>
                </div>
                <div class="account-balance negative">₪-2,180</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">EXCELLENCE</div>
                    <div class="account-subtitle">1 account</div>
                </div>
                <div class="account-balance">₪133,860</div>
            </div>
            <button class="view-all">View all accounts</button>
        </div>
    </div>
</body>
</html>
"""

GLASSMORPHISM_DARK_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%);
            min-height: 100%;
            padding: 1.5rem;
            line-height: 1.5;
        }}

        /* Glass Card Base - Dark */
        .glass {{
            background: rgba(0, 0, 0, 0.25);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
        }}

        /* Hero Card */
        .hero-card {{
            padding: 2rem 2.5rem;
            margin-bottom: 1.5rem;
            color: white;
        }}
        .hero-label {{
            font-size: 0.9rem;
            opacity: 0.8;
            font-weight: 500;
            margin-bottom: 0.25rem;
        }}
        .hero-amount {{
            font-size: 3rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 0.5rem;
        }}
        .hero-sync {{
            font-size: 0.85rem;
            opacity: 0.7;
        }}

        /* Metrics Row */
        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            padding: 1.25rem;
            text-align: center;
            color: white;
        }}
        .metric-value {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        .metric-label {{
            font-size: 0.8rem;
            opacity: 0.8;
            font-weight: 500;
        }}
        .metric-sublabel {{
            font-size: 0.7rem;
            opacity: 0.6;
            margin-top: 0.25rem;
        }}

        /* Budget Progress */
        .budget-card {{
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
            color: white;
        }}
        .budget-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .budget-title {{
            font-weight: 600;
        }}
        .budget-remaining {{
            font-size: 0.9rem;
            color: #6ee7b7;
            font-weight: 500;
        }}
        .budget-bar-bg {{
            height: 10px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }}
        .budget-bar {{
            height: 100%;
            background: linear-gradient(90deg, #10b981, #34d399);
            border-radius: 999px;
            width: 69%;
        }}
        .budget-details {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            opacity: 0.7;
        }}

        /* Insight Banner */
        .insight-banner {{
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 16px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: #6ee7b7;
        }}
        .insight-icon {{
            font-size: 1.25rem;
        }}
        .insight-message {{
            font-weight: 500;
            font-size: 0.9rem;
        }}

        /* Alerts */
        .alerts-section {{
            margin-bottom: 1.5rem;
        }}
        .section-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            color: rgba(255, 255, 255, 0.9);
        }}
        .alert-card {{
            background: rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: rgba(255, 255, 255, 0.9);
        }}
        .alert-card.sync {{
            border-left: 4px solid #fbbf24;
        }}
        .alert-card.category {{
            border-left: 4px solid #a78bfa;
        }}
        .alert-message {{
            flex: 1;
            font-size: 0.9rem;
        }}
        .alert-action {{
            padding: 0.5rem 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            font-size: 0.8rem;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.15);
            cursor: pointer;
        }}
        .alert-action:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}

        /* Two Column Layout */
        .two-columns {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 1.5rem;
        }}

        /* Cards */
        .card {{
            padding: 1.25rem 1.5rem;
            color: white;
        }}
        .card-header {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .date-header {{
            font-size: 0.7rem;
            font-weight: 600;
            opacity: 0.6;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0.75rem 0 0.5rem 0;
        }}
        .date-header:first-of-type {{
            margin-top: 0;
        }}
        .txn-item {{
            display: flex;
            align-items: center;
            padding: 0.6rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .txn-item:last-child {{
            border-bottom: none;
        }}
        .txn-icon {{
            font-size: 1.2rem;
            width: 32px;
            text-align: center;
        }}
        .txn-details {{
            flex: 1;
            margin-left: 0.5rem;
        }}
        .txn-merchant {{
            font-weight: 500;
            font-size: 0.9rem;
        }}
        .txn-category {{
            display: inline-block;
            font-size: 0.65rem;
            padding: 0.1rem 0.5rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.1);
            margin-top: 0.15rem;
        }}
        .txn-amount {{
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-weight: 500;
            font-size: 0.9rem;
            color: #f87171;
        }}

        /* Account Item */
        .account-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            margin-bottom: 0.5rem;
        }}
        .account-item:last-child {{
            margin-bottom: 0;
        }}
        .account-name {{
            font-weight: 600;
            font-size: 0.95rem;
        }}
        .account-subtitle {{
            font-size: 0.8rem;
            opacity: 0.6;
        }}
        .account-balance {{
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-weight: 500;
        }}
        .account-balance.negative {{
            color: #f87171;
        }}

        /* View All Button */
        .view-all {{
            display: block;
            width: 100%;
            margin-top: 1rem;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.8);
            cursor: pointer;
            text-align: center;
        }}
        .view-all:hover {{
            background: rgba(255, 255, 255, 0.15);
            color: white;
        }}
    </style>
</head>
<body>
    <!-- Hero Card -->
    <div class="hero-card glass">
        <div class="hero-label">Net Worth</div>
        <div class="hero-amount">{SAMPLE_DATA['net_worth']}</div>
        <div class="hero-sync">Last synced {SAMPLE_DATA['last_sync']}</div>
    </div>

    <!-- Metrics Row -->
    <div class="metrics-row">
        <div class="metric-card glass">
            <div class="metric-value">{SAMPLE_DATA['monthly_spending']}</div>
            <div class="metric-label">This Month</div>
            <div class="metric-sublabel">spent</div>
        </div>
        <div class="metric-card glass">
            <div class="metric-value">{SAMPLE_DATA['pending_count']}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-sublabel">{SAMPLE_DATA['pending_amount']}</div>
        </div>
        <div class="metric-card glass">
            <div class="metric-value">{SAMPLE_DATA['account_count']}</div>
            <div class="metric-label">Accounts</div>
            <div class="metric-sublabel">{SAMPLE_DATA['transaction_count']} txns</div>
        </div>
    </div>

    <!-- Budget Progress -->
    <div class="budget-card glass">
        <div class="budget-header">
            <span class="budget-title">Monthly Budget</span>
            <span class="budget-remaining">{SAMPLE_DATA['budget_remaining']} remaining</span>
        </div>
        <div class="budget-bar-bg">
            <div class="budget-bar"></div>
        </div>
        <div class="budget-details">
            <span>₪{SAMPLE_DATA['budget_spent']:,} of ₪{SAMPLE_DATA['budget_total']:,}</span>
            <span>{SAMPLE_DATA['budget_percent']}%</span>
        </div>
    </div>

    <!-- Insight Banner -->
    <div class="insight-banner">
        <span class="insight-icon">📈</span>
        <span class="insight-message">{SAMPLE_DATA['insight']}</span>
    </div>

    <!-- Alerts -->
    <div class="alerts-section">
        <div class="section-title">Needs Attention</div>
        <div class="alert-card sync">
            <span>⚠️</span>
            <span class="alert-message">{SAMPLE_DATA['alerts'][0]['message']}</span>
            <button class="alert-action">Sync Now</button>
        </div>
        <div class="alert-card category">
            <span>🏷️</span>
            <span class="alert-message">{SAMPLE_DATA['alerts'][1]['message']}</span>
            <button class="alert-action">Review</button>
        </div>
    </div>

    <!-- Two Column Layout -->
    <div class="two-columns">
        <!-- Recent Activity -->
        <div class="card glass">
            <div class="card-header">📋 Recent Activity</div>
            <div class="date-header">Today</div>
            <div class="txn-item">
                <span class="txn-icon">🛒</span>
                <div class="txn-details">
                    <div class="txn-merchant">Shufersal Deal</div>
                    <span class="txn-category">groceries</span>
                </div>
                <span class="txn-amount">-₪287</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">⛽</span>
                <div class="txn-details">
                    <div class="txn-merchant">Sonol Gas Station</div>
                    <span class="txn-category">fuel</span>
                </div>
                <span class="txn-amount">-₪350</span>
            </div>
            <div class="date-header">Yesterday</div>
            <div class="txn-item">
                <span class="txn-icon">🍕</span>
                <div class="txn-details">
                    <div class="txn-merchant">Domino's Pizza</div>
                    <span class="txn-category">restaurants</span>
                </div>
                <span class="txn-amount">-₪89</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">📱</span>
                <div class="txn-details">
                    <div class="txn-merchant">Partner Cellular</div>
                    <span class="txn-category">subscriptions</span>
                </div>
                <span class="txn-amount">-₪99</span>
            </div>
            <button class="view-all">View all transactions</button>
        </div>

        <!-- Accounts Summary -->
        <div class="card glass">
            <div class="card-header">🏦 Accounts</div>
            <div class="account-item">
                <div>
                    <div class="account-name">CAL</div>
                    <div class="account-subtitle">2 cards</div>
                </div>
                <div class="account-balance negative">₪-4,230</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">MAX</div>
                    <div class="account-subtitle">1 card</div>
                </div>
                <div class="account-balance negative">₪-2,180</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">EXCELLENCE</div>
                    <div class="account-subtitle">1 account</div>
                </div>
                <div class="account-balance">₪133,860</div>
            </div>
            <button class="view-all">View all accounts</button>
        </div>
    </div>
</body>
</html>
"""

# ============================================================================
# STYLE 3: PURE MATERIAL DESIGN
# ============================================================================

MATERIAL_LIGHT_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafafa;
            color: #1c1b1f;
            padding: 1.5rem;
            line-height: 1.5;
        }}

        /* Material 3 Surface */
        .surface {{
            background: white;
            border-radius: 12px;
        }}
        .surface-1 {{
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }}
        .surface-2 {{
            box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08);
        }}

        /* Hero Card - Material Filled Tonal */
        .hero-card {{
            background: #1976d2;
            border-radius: 28px;
            padding: 2rem 2.5rem;
            color: white;
            margin-bottom: 1.5rem;
        }}
        .hero-label {{
            font-size: 0.875rem;
            opacity: 0.9;
            font-weight: 500;
            margin-bottom: 0.25rem;
            letter-spacing: 0.1px;
        }}
        .hero-amount {{
            font-size: 2.75rem;
            font-weight: 400;
            line-height: 1.1;
            margin-bottom: 0.5rem;
        }}
        .hero-sync {{
            font-size: 0.875rem;
            opacity: 0.8;
        }}

        /* Metrics Row */
        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            padding: 1rem 1.25rem;
            text-align: center;
            background: #e3f2fd;
            border-radius: 12px;
        }}
        .metric-value {{
            font-size: 1.5rem;
            font-weight: 500;
            color: #1c1b1f;
            margin-bottom: 0.25rem;
        }}
        .metric-label {{
            font-size: 0.75rem;
            color: #49454f;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-sublabel {{
            font-size: 0.75rem;
            color: #79747e;
            margin-top: 0.25rem;
        }}

        /* Budget Progress - Material Linear Progress */
        .budget-card {{
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .budget-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .budget-title {{
            font-weight: 500;
            color: #1c1b1f;
            font-size: 0.875rem;
        }}
        .budget-remaining {{
            font-size: 0.875rem;
            color: #2e7d32;
            font-weight: 500;
        }}
        .budget-bar-bg {{
            height: 4px;
            background: #c8e6c9;
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }}
        .budget-bar {{
            height: 100%;
            background: #2e7d32;
            border-radius: 2px;
            width: 69%;
        }}
        .budget-details {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #49454f;
        }}

        /* Insight Banner - Material Filled Banner */
        .insight-banner {{
            background: #e8f5e9;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .insight-icon {{
            font-size: 1.25rem;
        }}
        .insight-message {{
            color: #1b5e20;
            font-weight: 400;
            font-size: 0.875rem;
        }}

        /* Alerts - Material List */
        .alerts-section {{
            margin-bottom: 1.5rem;
        }}
        .section-title {{
            font-size: 0.6875rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
            color: #49454f;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .alert-card {{
            border-radius: 0;
            padding: 1rem 1.25rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            background: white;
            border-bottom: 1px solid #e7e0ec;
        }}
        .alert-card:first-of-type {{
            border-radius: 12px 12px 0 0;
        }}
        .alert-card:last-of-type {{
            border-radius: 0 0 12px 12px;
            border-bottom: none;
        }}
        .alert-card:only-of-type {{
            border-radius: 12px;
        }}
        .alert-icon-container {{
            width: 40px;
            height: 40px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }}
        .alert-icon-container.sync {{
            background: #fff3e0;
        }}
        .alert-icon-container.category {{
            background: #ede7f6;
        }}
        .alert-message {{
            flex: 1;
            font-size: 0.875rem;
            color: #1c1b1f;
        }}
        .alert-action {{
            padding: 0.625rem 1.25rem;
            background: transparent;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
            color: #1976d2;
            border: none;
            cursor: pointer;
        }}
        .alert-action:hover {{
            background: #e3f2fd;
        }}

        /* Two Column Layout */
        .two-columns {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 1.5rem;
        }}

        /* Cards */
        .card {{
            padding: 1.25rem 1.5rem;
        }}
        .card-header {{
            font-size: 0.6875rem;
            font-weight: 500;
            color: #49454f;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e7e0ec;
        }}
        .date-header {{
            font-size: 0.6875rem;
            font-weight: 500;
            color: #79747e;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0.75rem 0 0.5rem 0;
        }}
        .date-header:first-of-type {{
            margin-top: 0;
        }}
        .txn-item {{
            display: flex;
            align-items: center;
            padding: 0.75rem 0;
        }}
        .txn-icon {{
            font-size: 1.25rem;
            width: 40px;
            height: 40px;
            background: #f5f5f5;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .txn-details {{
            flex: 1;
            margin-left: 1rem;
        }}
        .txn-merchant {{
            font-weight: 400;
            color: #1c1b1f;
            font-size: 0.875rem;
        }}
        .txn-category {{
            display: inline-block;
            font-size: 0.6875rem;
            padding: 0.125rem 0.5rem;
            border-radius: 8px;
            background: #e3f2fd;
            color: #1976d2;
            margin-top: 0.25rem;
            font-weight: 500;
        }}
        .txn-amount {{
            font-family: 'Roboto Mono', monospace;
            font-weight: 500;
            font-size: 0.875rem;
            color: #c62828;
        }}

        /* Account Item */
        .account-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            background: #f5f5f5;
            border-radius: 12px;
            margin-bottom: 0.5rem;
        }}
        .account-item:last-child {{
            margin-bottom: 0;
        }}
        .account-name {{
            font-weight: 500;
            color: #1c1b1f;
            font-size: 0.875rem;
        }}
        .account-subtitle {{
            font-size: 0.75rem;
            color: #79747e;
        }}
        .account-balance {{
            font-family: 'Roboto Mono', monospace;
            font-weight: 500;
            color: #1c1b1f;
        }}
        .account-balance.negative {{
            color: #c62828;
        }}

        /* View All Button - Material Text Button */
        .view-all {{
            display: block;
            width: 100%;
            margin-top: 1rem;
            padding: 0.625rem 1rem;
            background: transparent;
            border: none;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
            color: #1976d2;
            cursor: pointer;
            text-align: center;
        }}
        .view-all:hover {{
            background: #e3f2fd;
        }}
    </style>
</head>
<body>
    <!-- Hero Card -->
    <div class="hero-card">
        <div class="hero-label">Net Worth</div>
        <div class="hero-amount">{SAMPLE_DATA['net_worth']}</div>
        <div class="hero-sync">Last synced {SAMPLE_DATA['last_sync']}</div>
    </div>

    <!-- Metrics Row -->
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['monthly_spending']}</div>
            <div class="metric-label">This Month</div>
            <div class="metric-sublabel">spent</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['pending_count']}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-sublabel">{SAMPLE_DATA['pending_amount']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['account_count']}</div>
            <div class="metric-label">Accounts</div>
            <div class="metric-sublabel">{SAMPLE_DATA['transaction_count']} txns</div>
        </div>
    </div>

    <!-- Budget Progress -->
    <div class="budget-card surface surface-1">
        <div class="budget-header">
            <span class="budget-title">Monthly Budget</span>
            <span class="budget-remaining">{SAMPLE_DATA['budget_remaining']} remaining</span>
        </div>
        <div class="budget-bar-bg">
            <div class="budget-bar"></div>
        </div>
        <div class="budget-details">
            <span>₪{SAMPLE_DATA['budget_spent']:,} of ₪{SAMPLE_DATA['budget_total']:,}</span>
            <span>{SAMPLE_DATA['budget_percent']}%</span>
        </div>
    </div>

    <!-- Insight Banner -->
    <div class="insight-banner">
        <span class="insight-icon">📈</span>
        <span class="insight-message">{SAMPLE_DATA['insight']}</span>
    </div>

    <!-- Alerts -->
    <div class="alerts-section">
        <div class="section-title">Needs Attention</div>
        <div class="surface surface-1">
            <div class="alert-card">
                <div class="alert-icon-container sync">⚠️</div>
                <span class="alert-message">{SAMPLE_DATA['alerts'][0]['message']}</span>
                <button class="alert-action">Sync Now</button>
            </div>
            <div class="alert-card">
                <div class="alert-icon-container category">🏷️</div>
                <span class="alert-message">{SAMPLE_DATA['alerts'][1]['message']}</span>
                <button class="alert-action">Review</button>
            </div>
        </div>
    </div>

    <!-- Two Column Layout -->
    <div class="two-columns">
        <!-- Recent Activity -->
        <div class="card surface surface-2">
            <div class="card-header">📋 Recent Activity</div>
            <div class="date-header">Today</div>
            <div class="txn-item">
                <span class="txn-icon">🛒</span>
                <div class="txn-details">
                    <div class="txn-merchant">Shufersal Deal</div>
                    <span class="txn-category">groceries</span>
                </div>
                <span class="txn-amount">-₪287</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">⛽</span>
                <div class="txn-details">
                    <div class="txn-merchant">Sonol Gas Station</div>
                    <span class="txn-category">fuel</span>
                </div>
                <span class="txn-amount">-₪350</span>
            </div>
            <div class="date-header">Yesterday</div>
            <div class="txn-item">
                <span class="txn-icon">🍕</span>
                <div class="txn-details">
                    <div class="txn-merchant">Domino's Pizza</div>
                    <span class="txn-category">restaurants</span>
                </div>
                <span class="txn-amount">-₪89</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">📱</span>
                <div class="txn-details">
                    <div class="txn-merchant">Partner Cellular</div>
                    <span class="txn-category">subscriptions</span>
                </div>
                <span class="txn-amount">-₪99</span>
            </div>
            <button class="view-all">View all transactions</button>
        </div>

        <!-- Accounts Summary -->
        <div class="card surface surface-2">
            <div class="card-header">🏦 Accounts</div>
            <div class="account-item">
                <div>
                    <div class="account-name">CAL</div>
                    <div class="account-subtitle">2 cards</div>
                </div>
                <div class="account-balance negative">₪-4,230</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">MAX</div>
                    <div class="account-subtitle">1 card</div>
                </div>
                <div class="account-balance negative">₪-2,180</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">EXCELLENCE</div>
                    <div class="account-subtitle">1 account</div>
                </div>
                <div class="account-balance">₪133,860</div>
            </div>
            <button class="view-all">View all accounts</button>
        </div>
    </div>
</body>
</html>
"""

MATERIAL_DARK_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #121212;
            color: #e6e1e5;
            padding: 1.5rem;
            line-height: 1.5;
        }}

        /* Material 3 Dark Surface */
        .surface {{
            background: #1e1e1e;
            border-radius: 12px;
        }}
        .surface-1 {{
            background: #252525;
        }}
        .surface-2 {{
            background: #2d2d2d;
        }}

        /* Hero Card */
        .hero-card {{
            background: #3f51b5;
            border-radius: 28px;
            padding: 2rem 2.5rem;
            color: white;
            margin-bottom: 1.5rem;
        }}
        .hero-label {{
            font-size: 0.875rem;
            opacity: 0.9;
            font-weight: 500;
            margin-bottom: 0.25rem;
            letter-spacing: 0.1px;
        }}
        .hero-amount {{
            font-size: 2.75rem;
            font-weight: 400;
            line-height: 1.1;
            margin-bottom: 0.5rem;
        }}
        .hero-sync {{
            font-size: 0.875rem;
            opacity: 0.8;
        }}

        /* Metrics Row */
        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            padding: 1rem 1.25rem;
            text-align: center;
            background: #1e3a5f;
            border-radius: 12px;
        }}
        .metric-value {{
            font-size: 1.5rem;
            font-weight: 500;
            color: #e6e1e5;
            margin-bottom: 0.25rem;
        }}
        .metric-label {{
            font-size: 0.75rem;
            color: #cac4d0;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-sublabel {{
            font-size: 0.75rem;
            color: #938f99;
            margin-top: 0.25rem;
        }}

        /* Budget Progress */
        .budget-card {{
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .budget-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .budget-title {{
            font-weight: 500;
            color: #e6e1e5;
            font-size: 0.875rem;
        }}
        .budget-remaining {{
            font-size: 0.875rem;
            color: #81c784;
            font-weight: 500;
        }}
        .budget-bar-bg {{
            height: 4px;
            background: #1b4332;
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }}
        .budget-bar {{
            height: 100%;
            background: #81c784;
            border-radius: 2px;
            width: 69%;
        }}
        .budget-details {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #cac4d0;
        }}

        /* Insight Banner */
        .insight-banner {{
            background: #1b4332;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .insight-icon {{
            font-size: 1.25rem;
        }}
        .insight-message {{
            color: #a5d6a7;
            font-weight: 400;
            font-size: 0.875rem;
        }}

        /* Alerts */
        .alerts-section {{
            margin-bottom: 1.5rem;
        }}
        .section-title {{
            font-size: 0.6875rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
            color: #cac4d0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .alert-card {{
            border-radius: 0;
            padding: 1rem 1.25rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            background: #2d2d2d;
            border-bottom: 1px solid #3d3d3d;
        }}
        .alert-card:first-of-type {{
            border-radius: 12px 12px 0 0;
        }}
        .alert-card:last-of-type {{
            border-radius: 0 0 12px 12px;
            border-bottom: none;
        }}
        .alert-card:only-of-type {{
            border-radius: 12px;
        }}
        .alert-icon-container {{
            width: 40px;
            height: 40px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }}
        .alert-icon-container.sync {{
            background: #4a3728;
        }}
        .alert-icon-container.category {{
            background: #2d2255;
        }}
        .alert-message {{
            flex: 1;
            font-size: 0.875rem;
            color: #e6e1e5;
        }}
        .alert-action {{
            padding: 0.625rem 1.25rem;
            background: transparent;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
            color: #90caf9;
            border: none;
            cursor: pointer;
        }}
        .alert-action:hover {{
            background: #1e3a5f;
        }}

        /* Two Column Layout */
        .two-columns {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 1.5rem;
        }}

        /* Cards */
        .card {{
            padding: 1.25rem 1.5rem;
        }}
        .card-header {{
            font-size: 0.6875rem;
            font-weight: 500;
            color: #cac4d0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #3d3d3d;
        }}
        .date-header {{
            font-size: 0.6875rem;
            font-weight: 500;
            color: #938f99;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0.75rem 0 0.5rem 0;
        }}
        .date-header:first-of-type {{
            margin-top: 0;
        }}
        .txn-item {{
            display: flex;
            align-items: center;
            padding: 0.75rem 0;
        }}
        .txn-icon {{
            font-size: 1.25rem;
            width: 40px;
            height: 40px;
            background: #3d3d3d;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .txn-details {{
            flex: 1;
            margin-left: 1rem;
        }}
        .txn-merchant {{
            font-weight: 400;
            color: #e6e1e5;
            font-size: 0.875rem;
        }}
        .txn-category {{
            display: inline-block;
            font-size: 0.6875rem;
            padding: 0.125rem 0.5rem;
            border-radius: 8px;
            background: #1e3a5f;
            color: #90caf9;
            margin-top: 0.25rem;
            font-weight: 500;
        }}
        .txn-amount {{
            font-family: 'Roboto Mono', monospace;
            font-weight: 500;
            font-size: 0.875rem;
            color: #ef9a9a;
        }}

        /* Account Item */
        .account-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            background: #3d3d3d;
            border-radius: 12px;
            margin-bottom: 0.5rem;
        }}
        .account-item:last-child {{
            margin-bottom: 0;
        }}
        .account-name {{
            font-weight: 500;
            color: #e6e1e5;
            font-size: 0.875rem;
        }}
        .account-subtitle {{
            font-size: 0.75rem;
            color: #938f99;
        }}
        .account-balance {{
            font-family: 'Roboto Mono', monospace;
            font-weight: 500;
            color: #e6e1e5;
        }}
        .account-balance.negative {{
            color: #ef9a9a;
        }}

        /* View All Button */
        .view-all {{
            display: block;
            width: 100%;
            margin-top: 1rem;
            padding: 0.625rem 1rem;
            background: transparent;
            border: none;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
            color: #90caf9;
            cursor: pointer;
            text-align: center;
        }}
        .view-all:hover {{
            background: #1e3a5f;
        }}
    </style>
</head>
<body>
    <!-- Hero Card -->
    <div class="hero-card">
        <div class="hero-label">Net Worth</div>
        <div class="hero-amount">{SAMPLE_DATA['net_worth']}</div>
        <div class="hero-sync">Last synced {SAMPLE_DATA['last_sync']}</div>
    </div>

    <!-- Metrics Row -->
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['monthly_spending']}</div>
            <div class="metric-label">This Month</div>
            <div class="metric-sublabel">spent</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['pending_count']}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-sublabel">{SAMPLE_DATA['pending_amount']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{SAMPLE_DATA['account_count']}</div>
            <div class="metric-label">Accounts</div>
            <div class="metric-sublabel">{SAMPLE_DATA['transaction_count']} txns</div>
        </div>
    </div>

    <!-- Budget Progress -->
    <div class="budget-card surface-1">
        <div class="budget-header">
            <span class="budget-title">Monthly Budget</span>
            <span class="budget-remaining">{SAMPLE_DATA['budget_remaining']} remaining</span>
        </div>
        <div class="budget-bar-bg">
            <div class="budget-bar"></div>
        </div>
        <div class="budget-details">
            <span>₪{SAMPLE_DATA['budget_spent']:,} of ₪{SAMPLE_DATA['budget_total']:,}</span>
            <span>{SAMPLE_DATA['budget_percent']}%</span>
        </div>
    </div>

    <!-- Insight Banner -->
    <div class="insight-banner">
        <span class="insight-icon">📈</span>
        <span class="insight-message">{SAMPLE_DATA['insight']}</span>
    </div>

    <!-- Alerts -->
    <div class="alerts-section">
        <div class="section-title">Needs Attention</div>
        <div class="surface-1">
            <div class="alert-card">
                <div class="alert-icon-container sync">⚠️</div>
                <span class="alert-message">{SAMPLE_DATA['alerts'][0]['message']}</span>
                <button class="alert-action">Sync Now</button>
            </div>
            <div class="alert-card">
                <div class="alert-icon-container category">🏷️</div>
                <span class="alert-message">{SAMPLE_DATA['alerts'][1]['message']}</span>
                <button class="alert-action">Review</button>
            </div>
        </div>
    </div>

    <!-- Two Column Layout -->
    <div class="two-columns">
        <!-- Recent Activity -->
        <div class="card surface-2">
            <div class="card-header">📋 Recent Activity</div>
            <div class="date-header">Today</div>
            <div class="txn-item">
                <span class="txn-icon">🛒</span>
                <div class="txn-details">
                    <div class="txn-merchant">Shufersal Deal</div>
                    <span class="txn-category">groceries</span>
                </div>
                <span class="txn-amount">-₪287</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">⛽</span>
                <div class="txn-details">
                    <div class="txn-merchant">Sonol Gas Station</div>
                    <span class="txn-category">fuel</span>
                </div>
                <span class="txn-amount">-₪350</span>
            </div>
            <div class="date-header">Yesterday</div>
            <div class="txn-item">
                <span class="txn-icon">🍕</span>
                <div class="txn-details">
                    <div class="txn-merchant">Domino's Pizza</div>
                    <span class="txn-category">restaurants</span>
                </div>
                <span class="txn-amount">-₪89</span>
            </div>
            <div class="txn-item">
                <span class="txn-icon">📱</span>
                <div class="txn-details">
                    <div class="txn-merchant">Partner Cellular</div>
                    <span class="txn-category">subscriptions</span>
                </div>
                <span class="txn-amount">-₪99</span>
            </div>
            <button class="view-all">View all transactions</button>
        </div>

        <!-- Accounts Summary -->
        <div class="card surface-2">
            <div class="card-header">🏦 Accounts</div>
            <div class="account-item">
                <div>
                    <div class="account-name">CAL</div>
                    <div class="account-subtitle">2 cards</div>
                </div>
                <div class="account-balance negative">₪-4,230</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">MAX</div>
                    <div class="account-subtitle">1 card</div>
                </div>
                <div class="account-balance negative">₪-2,180</div>
            </div>
            <div class="account-item">
                <div>
                    <div class="account-name">EXCELLENCE</div>
                    <div class="account-subtitle">1 account</div>
                </div>
                <div class="account-balance">₪133,860</div>
            </div>
            <button class="view-all">View all accounts</button>
        </div>
    </div>
</body>
</html>
"""

# ============================================================================
# PAGE LAYOUT
# ============================================================================

st.title("Style Preview")
st.caption("Compare 3 design approaches for the dashboard. Select a style and theme to preview.")

# Style selector
col1, col2 = st.columns([2, 1])

with col1:
    style = st.radio(
        "Design Style",
        ["Hybrid Material + Glassmorphism (Recommended)", "Full Glassmorphism", "Pure Material Design"],
        horizontal=True,
        help="Choose a design approach to preview"
    )

with col2:
    theme = st.radio(
        "Theme",
        ["Light", "Dark"],
        horizontal=True
    )

st.divider()

# Style descriptions
style_info = {
    "Hybrid Material + Glassmorphism (Recommended)": {
        "description": "Best of both worlds: Solid cards with subtle shadows for main content, glass effects for hero and floating elements. Modern, professional, and highly readable.",
        "pros": ["High readability", "Professional look", "Works well in both light/dark modes", "Good contrast for data-heavy content"],
        "cons": ["Less visually distinctive than pure glassmorphism"]
    },
    "Full Glassmorphism": {
        "description": "Trendy, modern aesthetic with frosted glass effects everywhere. Beautiful on colorful backgrounds but requires careful attention to contrast.",
        "pros": ["Very modern and trendy", "Unique visual identity", "Beautiful depth effects"],
        "cons": ["Lower contrast for text", "May be harder to read", "Background-dependent"]
    },
    "Pure Material Design": {
        "description": "Google's Material Design 3 guidelines. Clean, functional, and familiar. Prioritizes usability and accessibility.",
        "pros": ["Maximum readability", "Accessible", "Familiar patterns", "Consistent behavior"],
        "cons": ["More conservative look", "Less distinctive"]
    }
}

# Get the short style key
style_key = style.replace(" (Recommended)", "")

info = style_info.get(style_key) or style_info.get(style)
if info:
    with st.expander("Style Details", expanded=False):
        st.markdown(f"**{info['description']}**")
        col_pros, col_cons = st.columns(2)
        with col_pros:
            st.markdown("**Pros:**")
            for pro in info['pros']:
                st.markdown(f"- {pro}")
        with col_cons:
            st.markdown("**Cons:**")
            for con in info['cons']:
                st.markdown(f"- {con}")

# Render the selected mockup
is_dark = theme == "Dark"

if "Hybrid" in style:
    mockup_html = HYBRID_DARK_HTML if is_dark else HYBRID_LIGHT_HTML
elif "Glassmorphism" in style:
    mockup_html = GLASSMORPHISM_DARK_HTML if is_dark else GLASSMORPHISM_LIGHT_HTML
else:  # Material
    mockup_html = MATERIAL_DARK_HTML if is_dark else MATERIAL_LIGHT_HTML

# Render mockup in iframe
html(mockup_html, height=1250, scrolling=True)

# Footer
st.divider()
st.caption(
    "This is a mockup preview page. After choosing a style, the selected design will be implemented "
    "across all pages. Delete this page once the decision is made."
)
