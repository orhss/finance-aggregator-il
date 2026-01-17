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


# Light Mode Color Palette
LIGHT_PALETTE = ColorPalette(
    # Brand colors
    primary="#1976d2",
    secondary="#00897b",
    accent="#f9ca24",

    # Status colors
    success="#00897b",
    warning="#f57c00",
    error="#c62828",
    info="#1976d2",

    # Background colors
    bg_primary="#ffffff",
    bg_secondary="#f5f5f5",
    bg_tertiary="#e0e0e0",

    # Text colors
    text_primary="#212121",
    text_secondary="#424242",
    text_muted="#757575",

    # Border colors
    border_light="#e0e0e0",
    border_medium="#bdbdbd",
    border_heavy="#9e9e9e",

    # Financial colors
    income_color="#00897b",
    expense_color="#c62828",
    neutral_color="#757575",

    # Chart colors
    chart_primary="#1976d2",
    chart_secondary="#00897b",
    chart_tertiary="#f57c00",
    chart_quaternary="#f9ca24",

    # Category colors
    category_colors={
        'Food & Dining': '#ff6b6b',
        'Transportation': '#4ecdc4',
        'Shopping': '#45b7d1',
        'Entertainment': '#f9ca24',
        'Bills & Utilities': '#6c5ce7',
        'Healthcare': '#fd79a8',
        'Groceries': '#00b894',
        'Salary': '#00897b',
        'Investment': '#1976d2',
        'Transfer': '#95a5a6',
    }
)

# Dark Mode Color Palette (Following UX Best Practices)
# Based on: https://www.uxdesigninstitute.com/blog/dark-mode-design-practical-guide/
DARK_PALETTE = ColorPalette(
    # Brand colors (desaturated for dark mode - avoid visual jarring)
    primary="#5a9fd4",      # Subdued blue (from #1976d2 light mode)
    secondary="#5a9a94",    # Muted teal (from #00897b light mode)
    accent="#d4b95a",       # Muted gold (from #f9ca24 light mode)

    # Status colors (significantly desaturated)
    success="#5a9a94",      # Muted teal (success should be calm)
    warning="#c98850",      # Muted orange (from #f57c00)
    error="#b85858",        # Muted red (from #c62828)
    info="#5a9fd4",         # Subdued blue (consistent with primary)

    # Background colors (avoid pure black #000000 - use dark grey)
    bg_primary="#121212",   # Dark grey (UX best practice, not pure black)
    bg_secondary="#1e1e1e", # Slightly lighter grey
    bg_tertiary="#2a2a2a",  # Medium grey for elevation

    # Text colors (avoid pure white #FFFFFF - use off-white)
    text_primary="#e0e0e0", # Off-white (UX best practice)
    text_secondary="#b0b0b0",  # Light grey for secondary text
    text_muted="#808080",   # Medium grey for muted text

    # Border colors (subtle but visible)
    border_light="#2a2a2a",
    border_medium="#404040",
    border_heavy="#5a5a5a",

    # Financial colors (desaturated for better readability)
    income_color="#5a9a94",  # Muted teal (calm, positive)
    expense_color="#b85858", # Muted red (not aggressive)
    neutral_color="#808080", # Grey

    # Chart colors (desaturated, harmonious palette)
    chart_primary="#5a9fd4",   # Subdued blue
    chart_secondary="#5a9a94",  # Muted teal
    chart_tertiary="#c98850",   # Muted orange
    chart_quaternary="#d4b95a", # Muted gold

    # Category colors (desaturated versions - avoid bright/jarring colors)
    category_colors={
        'Food & Dining': '#c97676',      # Muted red (from #ff6b6b)
        'Transportation': '#6ba8a0',     # Muted teal (from #4ecdc4)
        'Shopping': '#6197ad',           # Muted blue (from #45b7d1)
        'Entertainment': '#d4b95a',      # Muted gold (from #ffd93d)
        'Bills & Utilities': '#8b7fc7',  # Muted purple (from #a78bfa)
        'Healthcare': '#c988a6',         # Muted pink (from #f687b3)
        'Groceries': '#5fa888',          # Muted green (from #34d399)
        'Salary': '#5a9a94',             # Muted teal
        'Investment': '#5a9fd4',         # Subdued blue
        'Transfer': '#8a939e',           # Muted grey-blue
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
        }}

        .stButton > button[kind="primary"] {{
            background-color: {self.palette.primary};
            color: white;
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
