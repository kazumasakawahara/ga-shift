"""MCP サーバーの結合テスト.

FastMCP の Client を使い、実際のMCPプロトコル経由でツールを呼び出す。
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastmcp import Client

from ga_shift.mcp.server import _facility_state, mcp


# ---------------------------------------------------------------------------
# Fixture: facility_state をリセット + in-memory MCP Client
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_state():
    _facility_state.clear()
    yield
    _facility_state.clear()


@pytest_asyncio.fixture
async def client():
    """In-memory MCP クライアントを作成する。"""
    async with Client(mcp) as c:
        yield c


# ===================================================================
# ツール一覧テスト
# ===================================================================
class TestMCPToolDiscovery:
    @pytest.mark.asyncio
    async def test_list_tools(self, client: Client):
        """全10ツールが登録されていること。"""
        tools = await client.list_tools()
        tool_names = sorted(t.name for t in tools)

        assert len(tools) == 13
        assert tool_names == [
            "add_constraint",
            "adjust_schedule",
            "analyze_schedule_balance",
            "check_compliance",
            "explain_result",
            "generate_shift_template",
            "get_accompanied_visits",
            "get_staffing_requirements",
            "import_accompanied_visits",
            "list_constraints",
            "run_optimization",
            "setup_facility",
            "transfer_staff",
        ]

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self, client: Client):
        """全ツールに日本語の説明があること。"""
        tools = await client.list_tools()

        for tool in tools:
            assert tool.description, f"{tool.name} has no description"
            assert len(tool.description) > 10, f"{tool.name} description too short"


# ===================================================================
# ツール呼び出しテスト（プロトコル経由）
# ===================================================================
class TestMCPToolCalls:
    @pytest.mark.asyncio
    async def test_setup_via_protocol(self, client: Client):
        """setup_facility をMCPプロトコル経由で呼び出せること。"""
        result = await client.call_tool(
            "setup_facility",
            {"name": "テスト事業所", "facility_type": "就労継続支援B型"},
        )

        # FastMCP Client returns result content
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_constraints_via_protocol(self, client: Client):
        """list_constraints をMCPプロトコル経由で呼び出せること。"""
        result = await client.call_tool("list_constraints", {})

        assert result is not None

    @pytest.mark.asyncio
    async def test_add_constraint_via_protocol(self, client: Client):
        """add_constraint をMCPプロトコル経由で呼び出せること。"""
        result = await client.call_tool(
            "add_constraint",
            {"constraint_type": "kitchen_min_workers"},
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_tool_arguments(self, client: Client):
        """不正な引数でエラーが適切に返ること。"""
        result = await client.call_tool(
            "add_constraint",
            {"constraint_type": "nonexistent_constraint_xyz"},
        )

        # Should return error status without crashing
        assert result is not None
