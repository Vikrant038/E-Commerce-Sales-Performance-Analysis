"""Headless integration test for streamlit_app.py using Streamlit AppTest."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def test_app_renders_without_exceptions():
    """Verify that streamlit_app.py boots, loads gold data, and renders without unhandled exceptions."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception, f"App raised an unhandled exception: {at.exception}"
    assert len(at.title) >= 1
    assert "E-Commerce Sales Performance" in at.title[0].value
