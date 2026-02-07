"""ComplianceAgent - 人員配置基準の充足確認エージェント.

福祉事業所の法的基準（人員配置基準）を確認し、
シフトが基準を満たしているかを報告する。

就労継続支援B型の主な基準:
- 職業指導員・生活支援員: 利用者10人に対し1人以上
- サービス管理責任者: 利用者60人以下で1人以上
- 管理者: 1人（兼務可）

フェーズC: 運用支援
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools


def create_compliance_agent(
    mcp_server_command: str | None = None,
) -> Agent:
    """コンプライアンスAgentを作成する.

    人員配置基準チェックと法令遵守の確認を行う。

    Args:
        mcp_server_command: GA-shift MCPサーバーの起動コマンド。

    Returns:
        設定済みのAgno Agent
    """
    ga_mcp = MCPTools(
        command=mcp_server_command or "uv run python -m ga_shift.mcp.server",
    )

    return Agent(
        name="コンプライアンスAgent",
        id="compliance-agent",
        model=Claude(id="claude-sonnet-4-5-20250929"),
        tools=[ga_mcp],
        instructions=[
            # ── 役割 ──
            "あなたは福祉事業所の人員配置基準を確認するエージェントです。",
            "シフトが法的基準を満たしているかを検証し、違反がある場合は",
            "具体的な改善策を提案します。",
            "",
            # ── 法的基準 ──
            "【就労継続支援B型の人員配置基準】",
            "1. 職業指導員・生活支援員",
            "   - 利用者数10人に対し1人以上（常勤換算）",
            "   - うち1人以上は常勤であること",
            "",
            "2. サービス管理責任者",
            "   - 利用者60人以下の場合、1人以上",
            "   - 利用者61人以上の場合、1人に加え60人超の40人ごとに1人追加",
            "",
            "3. 管理者",
            "   - 1人（他の職務との兼務可）",
            "",
            "4. 日中活動の最低人員",
            "   - 営業日ごとに最低限の人員配置が必要",
            "   - 利用者定員に応じた人員を確保",
            "",
            # ── チェック手順 ──
            "【チェック手順】",
            "1. get_staffing_requirements でその月の基準を確認",
            "2. check_compliance で現在のシフトの充足状況を確認",
            "3. 違反がある日をリストアップ",
            "4. 改善案を提示",
            "",
            # ── 報告 ──
            "【報告フォーマット】",
            "- 「適合」「要改善」「不適合」の3段階で評価",
            "- 不適合の日は具体的な日付と不足人数を明示",
            "- 改善案は実現可能な範囲で提示",
            "- 法令の根拠条文を参考情報として添える",
            "- 専門用語にはわかりやすい説明を付ける",
        ],
        markdown=True,
    )
