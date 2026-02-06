# Vulture whitelist - items here are intentionally "unused"
# See: https://github.com/jendrikseipp/vulture#ignoring-files

# Pytest fixtures used for side effects (patching) - the variable
# is not referenced but the fixture must be in the signature
patched_session_local  # noqa

# Smoke test imports - testing that modules load, not using the imports
retry_selenium_action  # noqa
retry_api_call  # noqa
LoginFailedError  # noqa
date_range_filter  # noqa
streamlit_app  # noqa

# Context manager __exit__ parameters - required by Python protocol
# even if not used in the implementation
exc_tb  # noqa
