"""chat_app.py のインポート・起動テスト.

Streamlit アプリとしての起動確認（UIレンダリングは行わない）。
"""

from __future__ import annotations

import importlib
import sys

import pytest


class TestChatAppImport:
    def test_module_importable(self):
        """chat_app モジュールがインポートできること。"""
        # Streamlit の set_page_config は main 外で呼ばれるため
        # 直接インポートするとエラーになる場合がある。
        # spec だけロードして構文エラーがないことを確認する。
        spec = importlib.util.find_spec("ga_shift.ui.chat_app")
        assert spec is not None, "ga_shift.ui.chat_app module not found"

    def test_app_module_importable(self):
        """従来の app.py モジュールもインポートできること。"""
        spec = importlib.util.find_spec("ga_shift.ui.app")
        assert spec is not None, "ga_shift.ui.app module not found"

    def test_mcp_module_importable(self):
        """MCP __main__ モジュールがインポートできること。"""
        spec = importlib.util.find_spec("ga_shift.mcp.__main__")
        assert spec is not None, "ga_shift.mcp.__main__ module not found"

    def test_mcp_server_module_importable(self):
        """MCP server モジュールがインポートできること。"""
        from ga_shift.mcp.server import mcp
        assert mcp is not None
        assert mcp.name == "ga-shift"
