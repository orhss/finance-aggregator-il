"""
Design Tokens for Hybrid Material + Glassmorphism Design System.

This module defines the visual design language used across the Streamlit UI.
All color, spacing, typography, and effect values should be sourced from here.

Usage:
    from streamlit_app.styles.design_tokens import TOKENS, get_css_variables

    # Access tokens directly
    primary_color = TOKENS['color']['primary']

    # Generate CSS custom properties
    css_vars = get_css_variables()
"""

from typing import Dict, Any


# =============================================================================
# DESIGN TOKENS
# =============================================================================

TOKENS: Dict[str, Any] = {
    # -------------------------------------------------------------------------
    # COLOR PALETTE - Light Mode
    # -------------------------------------------------------------------------
    "color": {
        # Primary brand colors (indigo/violet gradient base)
        "primary": "#6366f1",
        "primary_light": "#818cf8",
        "primary_dark": "#4f46e5",

        # Secondary accent
        "secondary": "#8b5cf6",
        "secondary_light": "#a78bfa",

        # Semantic colors
        "success": "#10b981",
        "success_light": "#34d399",
        "success_bg": "#d1fae5",
        "success_text": "#065f46",

        "warning": "#f59e0b",
        "warning_light": "#fbbf24",
        "warning_bg": "#fef3c7",
        "warning_text": "#92400e",

        "error": "#ef4444",
        "error_light": "#f87171",
        "error_bg": "#fee2e2",
        "error_text": "#991b1b",

        "info": "#3b82f6",
        "info_light": "#60a5fa",
        "info_bg": "#dbeafe",
        "info_text": "#1e40af",

        # Neutral colors
        "text_primary": "#1f2937",
        "text_secondary": "#6b7280",
        "text_muted": "#9ca3af",
        "text_inverse": "#ffffff",

        # Backgrounds
        "background": "#f8fafc",
        "surface": "#ffffff",
        "surface_hover": "#f9fafb",
        "surface_subtle": "#fafafa",

        # Borders
        "border": "#e5e7eb",
        "border_light": "#f3f4f6",
        "border_focus": "#6366f1",

        # Special
        "expense": "#dc2626",
        "income": "#16a34a",
        "pending": "#f59e0b",
    },

    # -------------------------------------------------------------------------
    # COLOR PALETTE - Dark Mode
    # -------------------------------------------------------------------------
    "color_dark": {
        # Primary brand colors
        "primary": "#818cf8",
        "primary_light": "#a5b4fc",
        "primary_dark": "#6366f1",

        # Secondary accent
        "secondary": "#a78bfa",
        "secondary_light": "#c4b5fd",

        # Semantic colors
        "success": "#34d399",
        "success_light": "#6ee7b7",
        "success_bg": "rgba(16, 185, 129, 0.15)",
        "success_text": "#6ee7b7",

        "warning": "#fbbf24",
        "warning_light": "#fcd34d",
        "warning_bg": "rgba(245, 158, 11, 0.15)",
        "warning_text": "#fcd34d",

        "error": "#f87171",
        "error_light": "#fca5a5",
        "error_bg": "rgba(239, 68, 68, 0.15)",
        "error_text": "#fca5a5",

        "info": "#60a5fa",
        "info_light": "#93c5fd",
        "info_bg": "rgba(59, 130, 246, 0.15)",
        "info_text": "#93c5fd",

        # Neutral colors
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "text_inverse": "#0f172a",

        # Backgrounds
        "background": "#0f172a",
        "surface": "#1e293b",
        "surface_hover": "#334155",
        "surface_subtle": "#0f172a",

        # Borders
        "border": "#334155",
        "border_light": "#1e293b",
        "border_focus": "#818cf8",

        # Special
        "expense": "#f87171",
        "income": "#34d399",
        "pending": "#fbbf24",
    },

    # -------------------------------------------------------------------------
    # GRADIENTS
    # -------------------------------------------------------------------------
    "gradient": {
        # Hero card gradient
        "hero": "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
        "hero_dark": "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",

        # Success gradient (for budget bar, positive indicators)
        "success": "linear-gradient(90deg, #10b981, #34d399)",

        # Decorative overlay for hero
        "hero_overlay": "radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%)",
        "hero_overlay_dark": "radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%)",
    },

    # -------------------------------------------------------------------------
    # SPACING SCALE (based on 4px grid)
    # -------------------------------------------------------------------------
    "spacing": {
        "xs": "0.25rem",    # 4px
        "sm": "0.5rem",     # 8px
        "md": "1rem",       # 16px
        "lg": "1.5rem",     # 24px
        "xl": "2rem",       # 32px
        "2xl": "2.5rem",    # 40px
        "3xl": "3rem",      # 48px
    },

    # -------------------------------------------------------------------------
    # BORDER RADIUS
    # -------------------------------------------------------------------------
    "radius": {
        "sm": "6px",
        "md": "12px",
        "lg": "16px",
        "xl": "20px",
        "2xl": "24px",
        "full": "9999px",
    },

    # -------------------------------------------------------------------------
    # SHADOWS (Material-inspired elevation)
    # -------------------------------------------------------------------------
    "shadow": {
        "sm": "0 1px 2px rgba(0,0,0,0.05)",
        "md": "0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04)",
        "lg": "0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.04)",
        "xl": "0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)",
        "hero": "0 25px 50px -12px rgba(99, 102, 241, 0.25)",

        # Dark mode shadows
        "sm_dark": "0 1px 2px rgba(0,0,0,0.2)",
        "md_dark": "0 4px 6px -1px rgba(0,0,0,0.3), 0 2px 4px -1px rgba(0,0,0,0.2)",
        "lg_dark": "0 10px 15px -3px rgba(0,0,0,0.3), 0 4px 6px -2px rgba(0,0,0,0.2)",
        "hero_dark": "0 25px 50px -12px rgba(79, 70, 229, 0.3)",
    },

    # -------------------------------------------------------------------------
    # GLASSMORPHISM EFFECTS (for floating elements)
    # -------------------------------------------------------------------------
    "glass": {
        "background": "rgba(255, 255, 255, 0.85)",
        "background_dark": "rgba(30, 41, 59, 0.85)",
        "blur": "12px",
        "border": "rgba(255, 255, 255, 0.3)",
        "border_dark": "rgba(255, 255, 255, 0.1)",
    },

    # -------------------------------------------------------------------------
    # TYPOGRAPHY
    # -------------------------------------------------------------------------
    "typography": {
        "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "font_mono": "'SF Mono', 'Roboto Mono', Consolas, monospace",

        # Font sizes
        "size_xs": "0.65rem",
        "size_sm": "0.75rem",
        "size_base": "0.875rem",
        "size_md": "1rem",
        "size_lg": "1.25rem",
        "size_xl": "1.5rem",
        "size_2xl": "2rem",
        "size_3xl": "2.5rem",
        "size_hero": "3rem",

        # Font weights
        "weight_normal": "400",
        "weight_medium": "500",
        "weight_semibold": "600",
        "weight_bold": "700",

        # Line heights
        "leading_tight": "1.1",
        "leading_normal": "1.5",
        "leading_relaxed": "1.75",
    },

    # -------------------------------------------------------------------------
    # TRANSITIONS
    # -------------------------------------------------------------------------
    "transition": {
        "fast": "150ms ease",
        "normal": "200ms ease",
        "slow": "300ms ease",
        "spring": "300ms cubic-bezier(0.34, 1.56, 0.64, 1)",
    },

    # -------------------------------------------------------------------------
    # BREAKPOINTS (for responsive design)
    # -------------------------------------------------------------------------
    "breakpoint": {
        "sm": "640px",
        "md": "768px",
        "lg": "1024px",
        "xl": "1280px",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_css_variables(dark_mode: bool = False) -> str:
    """
    Generate CSS custom properties from tokens.

    Args:
        dark_mode: If True, use dark mode color palette

    Returns:
        CSS string with :root variables
    """
    color_key = "color_dark" if dark_mode else "color"
    colors = TOKENS[color_key]
    gradients = TOKENS["gradient"]
    spacing = TOKENS["spacing"]
    radius = TOKENS["radius"]
    shadows = TOKENS["shadow"]
    glass = TOKENS["glass"]
    typography = TOKENS["typography"]
    transitions = TOKENS["transition"]

    shadow_suffix = "_dark" if dark_mode else ""

    css_vars = [":root {"]

    # Colors
    for name, value in colors.items():
        css_vars.append(f"    --color-{name.replace('_', '-')}: {value};")

    # Gradients
    hero_gradient = gradients["hero_dark"] if dark_mode else gradients["hero"]
    hero_overlay = gradients["hero_overlay_dark"] if dark_mode else gradients["hero_overlay"]
    css_vars.append(f"    --gradient-hero: {hero_gradient};")
    css_vars.append(f"    --gradient-hero-overlay: {hero_overlay};")
    css_vars.append(f"    --gradient-success: {gradients['success']};")

    # Spacing
    for name, value in spacing.items():
        css_vars.append(f"    --spacing-{name}: {value};")

    # Radius
    for name, value in radius.items():
        css_vars.append(f"    --radius-{name}: {value};")

    # Shadows
    css_vars.append(f"    --shadow-sm: {shadows.get(f'sm{shadow_suffix}', shadows['sm'])};")
    css_vars.append(f"    --shadow-md: {shadows.get(f'md{shadow_suffix}', shadows['md'])};")
    css_vars.append(f"    --shadow-lg: {shadows.get(f'lg{shadow_suffix}', shadows['lg'])};")
    css_vars.append(f"    --shadow-hero: {shadows.get(f'hero{shadow_suffix}', shadows['hero'])};")

    # Glass effects
    glass_bg = glass["background_dark"] if dark_mode else glass["background"]
    glass_border = glass["border_dark"] if dark_mode else glass["border"]
    css_vars.append(f"    --glass-background: {glass_bg};")
    css_vars.append(f"    --glass-blur: {glass['blur']};")
    css_vars.append(f"    --glass-border: {glass_border};")

    # Typography
    css_vars.append(f"    --font-family: {typography['font_family']};")
    css_vars.append(f"    --font-mono: {typography['font_mono']};")
    for name, value in typography.items():
        if name.startswith("size_") or name.startswith("weight_") or name.startswith("leading_"):
            css_vars.append(f"    --{name.replace('_', '-')}: {value};")

    # Transitions
    for name, value in transitions.items():
        css_vars.append(f"    --transition-{name}: {value};")

    css_vars.append("}")

    return "\n".join(css_vars)


def get_token(path: str, dark_mode: bool = False) -> Any:
    """
    Get a token value by dot-notation path.

    Args:
        path: Dot-notation path like "color.primary" or "spacing.md"
        dark_mode: If True and path starts with "color", use dark mode colors

    Returns:
        The token value

    Example:
        get_token("color.primary")  # "#6366f1"
        get_token("spacing.lg")     # "1.5rem"
    """
    parts = path.split(".")

    # Handle color with dark mode override
    if parts[0] == "color" and dark_mode:
        parts[0] = "color_dark"

    value = TOKENS
    for part in parts:
        value = value[part]
    return value


# =============================================================================
# COMPONENT-SPECIFIC TOKEN HELPERS
# =============================================================================

def get_hero_styles(dark_mode: bool = False) -> dict:
    """Get complete style dict for hero card."""
    return {
        "background": TOKENS["gradient"]["hero_dark" if dark_mode else "hero"],
        "overlay": TOKENS["gradient"]["hero_overlay_dark" if dark_mode else "hero_overlay"],
        "shadow": TOKENS["shadow"]["hero_dark" if dark_mode else "hero"],
        "radius": TOKENS["radius"]["2xl"],
        "padding": f"{TOKENS['spacing']['xl']} {TOKENS['spacing']['2xl']}",
    }


def get_card_styles(dark_mode: bool = False) -> dict:
    """Get complete style dict for standard cards."""
    colors = TOKENS["color_dark" if dark_mode else "color"]
    return {
        "background": colors["surface"],
        "border": f"1px solid {colors['border_light']}",
        "shadow": TOKENS["shadow"]["md_dark" if dark_mode else "md"],
        "radius": TOKENS["radius"]["lg"],
        "padding": TOKENS["spacing"]["lg"],
    }


def get_metric_card_styles(dark_mode: bool = False) -> dict:
    """Get complete style dict for metric cards."""
    colors = TOKENS["color_dark" if dark_mode else "color"]
    return {
        "background": colors["surface"],
        "border": f"1px solid {colors['border_light']}",
        "shadow": TOKENS["shadow"]["md_dark" if dark_mode else "md"],
        "radius": TOKENS["radius"]["lg"],
        "padding": f"{TOKENS['spacing']['md']} {TOKENS['spacing']['lg']}",
    }
