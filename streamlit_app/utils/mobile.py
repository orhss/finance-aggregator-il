"""
Mobile detection utilities for Streamlit.

Automatic mobile detection via:
1. Query param (set by JS viewport detection)
2. User-Agent header fallback (real mobile devices)
"""

import streamlit as st
import streamlit.components.v1 as components

# Mobile user-agent patterns
MOBILE_PATTERNS = [
    'mobile', 'android', 'iphone', 'ipad', 'ipod',
    'blackberry', 'windows phone', 'opera mini', 'iemobile'
]

MOBILE_BREAKPOINT = 768  # pixels


def _detect_from_user_agent() -> bool:
    """Detect mobile from User-Agent header."""
    try:
        headers = st.context.headers
        user_agent = headers.get("User-Agent", "").lower()
        return any(pattern in user_agent for pattern in MOBILE_PATTERNS)
    except Exception:
        return False


def detect_mobile():
    """
    Automatic mobile detection.

    Flow:
    1. If ?mobile param exists → use it (was set by JS detection)
    2. If no param → inject JS to detect viewport and redirect with param
    3. User-Agent fallback for real mobile devices
    """
    query_params = st.query_params

    # Already have mobile param (set by JS or manual)
    if 'mobile' in query_params:
        st.session_state.is_mobile = query_params['mobile'] == 'true'
        st.session_state._mobile_detection_done = True
        return

    # Check User-Agent for real mobile devices
    if _detect_from_user_agent():
        st.session_state.is_mobile = True
        st.session_state._mobile_detection_done = True
        return

    # Only inject JS once per session to avoid multiple iframes
    if st.session_state.get('_mobile_detection_done'):
        return

    # Mark as done before injecting to prevent duplicates on re-runs
    st.session_state._mobile_detection_done = True

    # No param yet - inject JS to detect viewport and redirect
    # This runs once, then redirects with ?mobile=true/false
    components.html(
        f"""
        <script>
            (function() {{
                const isMobile = window.innerWidth < {MOBILE_BREAKPOINT};
                const currentUrl = window.parent.location.href;
                const url = new URL(currentUrl);

                // Only redirect if we don't already have the param
                if (!url.searchParams.has('mobile')) {{
                    url.searchParams.set('mobile', isMobile ? 'true' : 'false');
                    window.parent.location.href = url.toString();
                }}
            }})();
        </script>
        """,
        height=0,
    )

    # Default to desktop while JS redirects
    st.session_state.is_mobile = False


def render_mobile_toggle():
    """
    Render a toggle link to switch between mobile and desktop views.
    Shows in sidebar. Useful for manual override.
    """
    current_mobile = is_mobile()

    if current_mobile:
        st.sidebar.markdown("[🖥️ Switch to Desktop](?mobile=false)")
    else:
        st.sidebar.markdown("[📱 Switch to Mobile](?mobile=true)")


def is_mobile() -> bool:
    """
    Check if current session is on a mobile device.

    Returns:
        True if mobile device detected, False otherwise
    """
    return st.session_state.get('is_mobile', False)


def mobile_page_config():
    """
    Configure page for mobile-optimized experience.

    Call this instead of st.set_page_config() for mobile pages.
    Sets collapsed sidebar and wide layout.
    """
    st.set_page_config(
        page_title="Fin Mobile",
        page_icon="📱",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def force_mobile_mode(enabled: bool = True):
    """
    Force mobile mode on/off for testing.

    Args:
        enabled: True to force mobile mode, False to force desktop
    """
    st.session_state.is_mobile = enabled


def get_viewport_class() -> str:
    """
    Get CSS class for current viewport.

    Returns:
        'mobile' or 'desktop' based on detection
    """
    return 'mobile' if is_mobile() else 'desktop'
