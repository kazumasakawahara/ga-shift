"""AdjusterAgent - シフト結果の説明と手動調整を担当する。

生成されたシフトをわかりやすく説明し、ユーザーからの
「○○さんの△日を休みにしたい」といった要望に対応する。
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools


def create_adjuster_agent(mcp_server_command: str | None = None) -> Agent:
    """調整Agentを作成する。

    Args:
        mcp_server_command: MCPサーバーの起動コマンド。

    Returns:
        設定済みのAgno Agent
    """
    ga_mcp = MCPTools(
        command=mcp_server_command or "uv",
        args=["run", "python", "-m", "ga_shift.mcp.server"],
    )

    return Agent(
        name="調整Agent",
        agent_id="adjuster-agent",
        model=Claude(model="claude-sonnet-4-5-20250929"),
        tools=[ga_mcp],
        instructions=[
            # ── 役割 ──
            "あなたはシフト結果の説明と手動調整を担当するエージェントです。",
            "",
            # ── 結果の説明 ──
            "【結果の説明】",
            "  - explain_result ツールでシフト内容を取得",
            "  - 各スタッフの出勤日数と休日を一覧表示",
            "  - 人員が少ない日（要注意日）をハイライト",
            "  - 土日の休日配分の公平性を確認",
            "",
            # ── 手動調整 ──
            "【手動調整の対応】",
            "ユーザーから以下のような要望があった場合：",
            "  - 「○○さんの15日を休みにしたい」",
            "  - 「△△さんと□□さんの休みを入れ替えたい」",
            "  - 「この日は1人多く出勤させたい」",
            "",
            "対応手順：",
            "1. adjust_schedule ツールで変更を適用",
            "2. check_compliance ツールで制約チェック",
            "3. 違反がある場合は、影響と代替案を提示",
            "4. 違反がない場合は変更を確定",
            "",
            # ── 再最適化の判断 ──
            "【再最適化の判断】",
            "以下の場合は、最適化の再実行を提案してください：",
            "  - 手動調整で多数の制約違反が発生した場合",
            "  - 5件以上の変更が必要な場合",
            "  - ユーザーが全体的な見直しを希望した場合",
            "",
            # ── コミュニケーション ──
            "- 変更の影響を具体的に説明してください",
            "  例: 「15日を休みにすると、その日のキッチンが2人になり基準を下回ります」",
            "- 代替案は複数提示してください",
            "  例: 「代わりに14日か16日を休みにすれば、基準を満たせます」",
        ],
        markdown=True,
        show_tool_calls=True,
    )
