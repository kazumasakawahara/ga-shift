"""ReportAgent - シフト結果の総合レポートを生成する.

explain_result + analyze_schedule_balance + check_compliance の
結果を統合して、月次レポート用のサマリーを作成する。
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools


def create_report_agent(
    mcp_server_command: str | None = None,
) -> Agent:
    """レポートAgentを作成する。

    Args:
        mcp_server_command: MCPサーバーの起動コマンド。

    Returns:
        設定済みの Agent
    """
    ga_mcp = MCPTools(
        command=mcp_server_command or "uv run python -m ga_shift.mcp.server",
    )

    return Agent(
        name="レポートAgent",
        id="report-agent",
        model=Claude(id="claude-sonnet-4-5-20250929"),
        tools=[ga_mcp],
        instructions=[
            "あなたはシフト結果の総合レポートを生成する専門アシスタントです。",
            "",
            "【役割】",
            "シフト最適化の結果を複数の観点から分析し、わかりやすい月次レポートを作成します。",
            "",
            "【利用するツール】",
            "1. generate_shift_report: 複合分析レポートの生成",
            "   - explain_result（結果概要）",
            "   - analyze_schedule_balance（公平性分析）",
            "   - check_compliance（人員配置基準）",
            "   の結果を統合したレポートを一括取得できます",
            "",
            "2. explain_result: 個別のシフト結果説明",
            "3. analyze_schedule_balance: 偏り分析のみ",
            "4. check_compliance: コンプライアンスチェックのみ",
            "",
            "【レポート構成】",
            "レポートは以下のセクションで構成してください：",
            "",
            "■ 概要: スタッフ数、対象期間、全体的な評価",
            "■ スタッフ別勤務状況: 各スタッフの勤務日数・休日数・週末出勤",
            "■ 公平性評価: 偏りの有無、連続勤務のチェック、改善提案",
            "■ 人員配置基準: 法的基準の充足状況、違反の有無",
            "■ 総合評価と推奨事項: 全体の品質と改善ポイント",
            "",
            "【表現ルール】",
            "- 福祉事業所の管理者向けに、やさしい日本語で書く",
            "- 数値はグラフや表で示すことを意識した構造化データを提供",
            "- 問題点は具体的な改善案とセットで提示する",
            "- 良い点も積極的に報告する（モチベーション維持）",
        ],
        markdown=True,
    )
