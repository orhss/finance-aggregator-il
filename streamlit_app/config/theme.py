"""
Centralized Theme Configuration - Single source of truth for app theming

This module provides a DRY (Don't Repeat Yourself) theme system with light/dark modes.
All colors, styles, and theme-related constants are defined here.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ColorPalette:
    """Color palette for a theme mode"""
    # Brand colors
    primary: str
    secondary: str
    accent: str

    # Status colors
    success: str
    warning: str
    error: str
    info: str

    # Background colors
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str

    # Text colors
    text_primary: str
    text_secondary: str
    text_muted: str

    # Border colors
    border_light: str
    border_medium: str
    border_heavy: str

    # Financial colors
    income_color: str
    expense_color: str
    neutral_color: str

    # Chart colors
    chart_primary: str
    chart_secondary: str
    chart_tertiary: str
    chart_quaternary: str

    # Category colors (for badges)
    category_colors: Dict[str, str]


# Light Mode Color Palette - Hybrid Material + Glassmorphism
LIGHT_PALETTE = ColorPalette(
    # Brand colors (indigo/violet gradient base)
    primary="#6366f1",
    secondary="#8b5cf6",
    accent="#f59e0b",

    # Status colors
    success="#10b981",
    warning="#f59e0b",
    error="#ef4444",
    info="#3b82f6",

    # Background colors
    bg_primary="#f8fafc",
    bg_secondary="#ffffff",
    bg_tertiary="#f3f4f6",

    # Text colors
    text_primary="#1f2937",
    text_secondary="#6b7280",
    text_muted="#9ca3af",

    # Border colors
    border_light="#f3f4f6",
    border_medium="#e5e7eb",
    border_heavy="#e5e7eb",  # Used for button hover

    # Financial colors
    income_color="#16a34a",
    expense_color="#dc2626",
    neutral_color="#6b7280",

    # Chart colors
    chart_primary="#6366f1",
    chart_secondary="#8b5cf6",
    chart_tertiary="#10b981",
    chart_quaternary="#f59e0b",

    # Category colors
    category_colors={
        'Food & Dining': '#ef4444',
        'Transportation': '#06b6d4',
        'Shopping': '#3b82f6',
        'Entertainment': '#f59e0b',
        'Bills & Utilities': '#8b5cf6',
        'Healthcare': '#ec4899',
        'Groceries': '#10b981',
        'Salary': '#16a34a',
        'Investment': '#6366f1',
        'Transfer': '#6b7280',
    }
)

# Dark Mode Color Palette - Hybrid Material + Glassmorphism
# Based on UX best practices: avoid pure black, use desaturated colors
DARK_PALETTE = ColorPalette(
    # Brand colors (lighter for dark mode visibility)
    primary="#818cf8",      # Lighter indigo
    secondary="#a78bfa",    # Lighter violet
    accent="#fbbf24",       # Lighter amber

    # Status colors (desaturated for dark mode)
    success="#34d399",      # Lighter green
    warning="#fbbf24",      # Lighter amber
    error="#f87171",        # Lighter red
    info="#60a5fa",         # Lighter blue

    # Background colors (dark slate tones, not pure black)
    bg_primary="#0f172a",   # Slate 900
    bg_secondary="#1e293b", # Slate 800
    bg_tertiary="#334155",  # Slate 700

    # Text colors (off-white for reduced eye strain)
    text_primary="#f1f5f9", # Slate 100
    text_secondary="#94a3b8",  # Slate 400
    text_muted="#64748b",   # Slate 500

    # Border colors (subtle but visible)
    border_light="#1e293b",
    border_medium="#334155",
    border_heavy="#475569",

    # Financial colors (brighter for dark mode visibility)
    income_color="#34d399",  # Emerald 400
    expense_color="#f87171", # Red 400
    neutral_color="#64748b", # Slate 500

    # Chart colors (harmonious, visible on dark)
    chart_primary="#818cf8",   # Indigo 400
    chart_secondary="#a78bfa", # Violet 400
    chart_tertiary="#34d399",  # Emerald 400
    chart_quaternary="#fbbf24", # Amber 400

    # Category colors (brighter for dark mode)
    category_colors={
        'Food & Dining': '#f87171',      # Red 400
        'Transportation': '#22d3ee',     # Cyan 400
        'Shopping': '#60a5fa',           # Blue 400
        'Entertainment': '#fbbf24',      # Amber 400
        'Bills & Utilities': '#a78bfa',  # Violet 400
        'Healthcare': '#f472b6',         # Pink 400
        'Groceries': '#34d399',          # Emerald 400
        'Salary': '#4ade80',             # Green 400
        'Investment': '#818cf8',         # Indigo 400
        'Transfer': '#94a3b8',           # Slate 400
    }
)


class Theme:
    """
    Centralized theme manager - Single source of truth for all theming

    This class provides theme-aware colors, styles, and CSS that automatically
    adapt to the current theme mode (light/dark).
    """

    def __init__(self, mode: str = "light"):
        """
        Initialize theme

        Args:
            mode: Theme mode ("light" or "dark")
        """
        self.mode = mode
        self.palette = LIGHT_PALETTE if mode == "light" else DARK_PALETTE

    def get_color(self, color_name: str) -> str:
        """
        Get color by name from current theme palette

        Args:
            color_name: Name of color (e.g., "primary", "bg_primary")

        Returns:
            Hex color code
        """
        return getattr(self.palette, color_name, "#000000")

    def get_category_color(self, category: str) -> str:
        """
        Get color for a category

        Args:
            category: Category name

        Returns:
            Hex color code
        """
        return self.palette.category_colors.get(category, self.palette.text_muted)

    def get_amount_color(self, amount: float) -> str:
        """
        Get color for an amount (income/expense)

        Args:
            amount: Transaction amount

        Returns:
            Hex color code
        """
        if amount > 0:
            return self.palette.income_color
        elif amount < 0:
            return self.palette.expense_color
        else:
            return self.palette.neutral_color

    def get_status_color(self, status: str) -> str:
        """
        Get color for a status

        Args:
            status: Status name

        Returns:
            Hex color code
        """
        status_map = {
            'completed': self.palette.success,
            'pending': self.palette.warning,
            'failed': self.palette.error,
            'success': self.palette.success,
            'error': self.palette.error,
        }
        return status_map.get(status.lower(), self.palette.text_muted)

    def get_badge_style(
        self,
        bg_color: str,
        text_color: str = None,
        border_color: str = None
    ) -> str:
        """
        Generate CSS for a badge with theme-aware opacity

        Args:
            bg_color: Background color
            text_color: Text color (defaults to bg_color)
            border_color: Border color (defaults to bg_color with opacity)

        Returns:
            CSS style string
        """
        if text_color is None:
            text_color = bg_color
        if border_color is None:
            border_color = f"{bg_color}40"  # 25% opacity

        bg_opacity = "20" if self.mode == "light" else "30"

        return f"""
            display: inline-block;
            background-color: {bg_color}{bg_opacity};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 2px 10px;
            font-size: 0.85rem;
            font-weight: 500;
            margin: 2px;
        """

    def get_card_style(self, elevated: bool = False) -> str:
        """
        Generate CSS for a card component

        Args:
            elevated: Whether to add elevation/shadow

        Returns:
            CSS style string
        """
        # UX Best Practice: Shadows don't work well on dark backgrounds
        # Use outer glow (30% opacity) for dark mode instead
        if self.mode == "light":
            elevation_str = "box-shadow: 0 2px 8px rgba(0,0,0,0.1);" if elevated else ""
        else:
            # Dark mode: use subtle outer glow with 30% opacity for illumination effect
            elevation_str = "box-shadow: 0 0 16px rgba(255,255,255,0.05);" if elevated else ""

        return f"""
            background-color: {self.palette.bg_secondary};
            border: 1px solid {self.palette.border_light};
            border-radius: 8px;
            padding: 1rem;
            {elevation_str}
        """

    def generate_global_css(self) -> str:
        """
        Generate global CSS for the current theme

        Returns:
            CSS string with all theme-aware styles
        """
        return f"""
        <style>
        /* Theme: {self.mode.upper()} */

        :root {{
            --primary-color: {self.palette.primary};
            --secondary-color: {self.palette.secondary};
            --success-color: {self.palette.success};
            --warning-color: {self.palette.warning};
            --error-color: {self.palette.error};
            --bg-primary: {self.palette.bg_primary};
            --bg-secondary: {self.palette.bg_secondary};
            --text-primary: {self.palette.text_primary};
            --text-secondary: {self.palette.text_secondary};
            --border-color: {self.palette.border_light};
        }}

        /* Background colors */
        .stApp {{
            background-color: {self.palette.bg_primary};
            color: {self.palette.text_primary};
        }}

        /* Make Streamlit header transparent */
        [data-testid="stHeader"] {{
            background: transparent !important;
        }}
        [data-testid="stDecoration"] {{
            display: none !important;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {self.palette.bg_secondary};
            border-right: 1px solid {self.palette.border_light};
        }}

        /* Sidebar content - ensure text is visible */
        [data-testid="stSidebar"] * {{
            color: {self.palette.text_primary};
        }}

        /* Sidebar navigation links */
        [data-testid="stSidebar"] a {{
            color: {self.palette.primary} !important;
        }}

        /* Sidebar markdown */
        [data-testid="stSidebar"] .element-container {{
            color: {self.palette.text_primary};
        }}

        /* Sidebar labels */
        [data-testid="stSidebar"] label {{
            color: {self.palette.text_primary} !important;
        }}

        /* Cards and containers */
        .stContainer, [data-testid="stContainer"] {{
            background-color: {self.palette.bg_secondary};
        }}

        /* Metrics */
        [data-testid="stMetricValue"] {{
            color: {self.palette.text_primary};
        }}

        [data-testid="stMetricLabel"] {{
            color: {self.palette.text_secondary};
        }}

        /* Tables */
        [data-testid="stDataFrame"] {{
            background-color: {self.palette.bg_secondary};
            color: {self.palette.text_primary};
        }}

        /* Buttons */
        .stButton > button {{
            border-color: {self.palette.border_medium};
            color: {self.palette.text_primary} !important;
        }}

        /* Primary buttons */
        .stButton > button[kind="primary"] {{
            background-color: {self.palette.primary};
            color: white !important;
        }}

        /* Secondary buttons */
        .stButton > button[kind="secondary"] {{
            background-color: {self.palette.bg_tertiary};
            color: {self.palette.text_primary} !important;
            border-color: {self.palette.border_medium};
        }}

        /* Button text content (fixes markdown inside buttons) */
        .stButton > button p {{
            color: inherit !important;
        }}

        .stButton > button div {{
            color: inherit !important;
        }}

        .stButton > button span {{
            color: inherit !important;
        }}

        /* Button hover states */
        .stButton > button[kind="secondary"]:hover {{
            background-color: {self.palette.bg_secondary};
            border-color: {self.palette.primary};
        }}

        .stButton > button[kind="primary"]:hover {{
            opacity: 0.9;
        }}

        /* Inputs */
        input, textarea, select {{
            background-color: {self.palette.bg_secondary} !important;
            color: {self.palette.text_primary} !important;
            border-color: {self.palette.border_light} !important;
        }}

        /* Expanders */
        .streamlit-expanderHeader {{
            background-color: {self.palette.bg_secondary};
            color: {self.palette.text_primary};
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: {self.palette.bg_secondary};
            color: {self.palette.text_secondary};
        }}

        .stTabs [aria-selected="true"] {{
            background-color: {self.palette.primary}20;
            color: {self.palette.primary};
        }}

        /* Charts */
        [data-testid="stPlotlyChart"] {{
            background-color: {self.palette.bg_secondary};
        }}

        /* Headers */
        h1, h2, h3, h4, h5, h6 {{
            color: {self.palette.text_primary};
        }}

        /* Links */
        a {{
            color: {self.palette.primary};
        }}

        /* Code blocks */
        code {{
            background-color: {self.palette.bg_tertiary};
            color: {self.palette.text_primary};
        }}

        /* Dividers */
        hr {{
            border-color: {self.palette.border_light};
        }}

        /* Markdown text */
        .stMarkdown {{
            color: {self.palette.text_primary};
        }}

        /* All paragraph text */
        p {{
            color: {self.palette.text_primary};
        }}

        /* Captions */
        .stCaption {{
            color: {self.palette.text_secondary} !important;
        }}

        /* Radio and checkbox labels */
        label {{
            color: {self.palette.text_primary} !important;
        }}

        /* Select boxes */
        [data-baseweb="select"] {{
            background-color: {self.palette.bg_secondary} !important;
            color: {self.palette.text_primary} !important;
        }}

        /* Info/Warning/Error boxes */
        .stAlert {{
            color: {self.palette.text_primary};
        }}
        </style>
        """

    def get_chart_colors(self, count: int = 4) -> list:
        """
        Get list of chart colors for the current theme

        Args:
            count: Number of colors needed

        Returns:
            List of hex color codes
        """
        base_colors = [
            self.palette.chart_primary,
            self.palette.chart_secondary,
            self.palette.chart_tertiary,
            self.palette.chart_quaternary,
        ]

        # Repeat colors if more are needed
        colors = base_colors * (count // len(base_colors) + 1)
        return colors[:count]


# Global theme instance (singleton pattern)
_current_theme: Theme = None


def get_theme(mode: str = None) -> Theme:
    """
    Get the current theme instance (singleton)

    Args:
        mode: Theme mode ("light" or "dark"), None to get current

    Returns:
        Theme instance
    """
    global _current_theme

    if mode is not None or _current_theme is None:
        if mode is None:
            mode = "light"  # Default to light
        _current_theme = Theme(mode)

    return _current_theme


def set_theme_mode(mode: str) -> Theme:
    """
    Set the theme mode globally

    Args:
        mode: Theme mode ("light" or "dark")

    Returns:
        New theme instance
    """
    global _current_theme
    _current_theme = Theme(mode)
    return _current_theme
