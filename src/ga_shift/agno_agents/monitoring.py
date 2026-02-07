"""MonitoringAgent - シフト実績の偏り検出・報告エージェント.

生成されたシフト結果を分析し、以下を検出・報告する:
- スタッフ間の勤務日数や週末出勤の偏り
- 連続勤務の状況
- 実績と計画の乖離

フェーズC: 運用支援
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools


def create_monitoring_agent(
    mcp_server_command: str | None = None,
) -> Agent:
    """モニタリングAgentを作成する.

    シフト結果Excelを分析し、勤務の偏りや連勤状況を
    検出・報告する。

    Args:
        mcp_server_command: GA-shift MCPサーバーの起動コマンド。

    Returns:
        設定済みのAgno Agent
    """
    ga_mcp = MCPTools(
        command=mcp_server_command or "uv run python -m ga_shift.mcp.server",
    )

    return Agent(
        name="モニタリングAgent",
        id="monitoring-agent",
        model=Claude(id="claude-sonnet-4-5-20250929"),
        tools=[ga_mcp],
        instructions=[
            # ── 役割 ──
            "あなたはシフト実績を分析し、偏りや問題を報告するエージェントです。",
            "",
            # ── 分析項目 ──
            "【分析項目】",
            "以下の観点でシフト結果を分析してください：",
            "",
            "1. 勤務日数の公平性",
            "   - スタッフ間の月間勤務日数のばらつき",
            "   - 正規・パートそれぞれの平均と偏差",
            "   - 特定のスタッフに負担が偏っていないか",
            "",
            "2. 週末出勤の公平性",
            "   - 土日の出勤回数のスタッフ間比較",
            "   - 特定のスタッフばかり週末出勤になっていないか",
            "",
            "3. 連続勤務の状況",
            "   - 最大連続勤務日数（5日以上は注意、7日以上は警告）",
            "   - 連休の取得状況",
            "",
            "4. セクション別カバレッジ",
            "   - キッチンセクションの日別人員充足率",
            "   - 人員が薄い日の特定",
            "",
            # ── analyze_schedule_balance ──
            "【ツール使用】",
            "analyze_schedule_balance ツールを使うと、上記の分析を一度に実行できます。",
            "explain_result ツールで結果の詳細を確認することもできます。",
            "",
            # ── 報告フォーマット ──
            "【報告】",
            "- 問題の深刻度を「注意」「警告」「問題なし」で表現",
            "- 具体的な数値を示す（◯◯さんは△△日勤務、平均より□日多い等）",
            "- 改善提案を添える（「◯◯さんの15日を休日にすると均等になります」等）",
            "- わかりやすい日本語で報告してください",
        ],
        markdown=True,
    )
