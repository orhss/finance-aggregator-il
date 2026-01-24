"""
Mobile detection utilities for Streamlit.

Provides mobile device detection via JavaScript user-agent detection
and query parameter fallback.
"""

import streamlit as st
import streamlit.components.v1 as components


def detect_mobile():
    """
    Detect if user is on a mobile device using JavaScript user-agent detection.

    This injects a small JavaScript snippet that:
    1. Checks the user agent for mobile patterns
    2. Sets a query parameter if mobile is detected
    3. Stores result in session state

    Call this at the top of pages that need mobile-aware rendering.
    """
    # Check if we already detected mobile in this session
    if 'is_mobile' in st.session_state:
        return

    # Check query params first (for fallback/testing)
    query_params = st.query_params
    if 'mobile' in query_params:
        st.session_state.is_mobile = query_params['mobile'] == 'true'
        return

    # Inject JavaScript for mobile detection
    # This runs once and sets a query param that Streamlit can read
    mobile_detection_js = """
    <script>
    (function() {
        // Check if already detected
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('mobile')) return;

        // Mobile detection regex
        const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
        const isMobile = mobileRegex.test(navigator.userAgent);

        // Also check for small viewport (tablets in portrait, etc.)
        const isSmallViewport = window.innerWidth <= 768;

        if (isMobile || isSmallViewport) {
            // Add mobile=true to query params
            urlParams.set('mobile', 'true');
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.history.replaceState({}, '', newUrl);
            window.location.reload();
        } else {
            // Set mobile=false
            urlParams.set('mobile', 'false');
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.history.replaceState({}, '', newUrl);
        }
    })();
    </script>
    """

    # Inject with minimal height
    components.html(mobile_detection_js, height=0)

    # Default to desktop until JS runs
    st.session_state.is_mobile = False


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
