"""HandoverAgent - 人事異動対応エージェント.

スタッフの入退社・異動に対応し、事業所設定を更新する。
Agno Memory と連携し、過去の設定との差分を管理する。

フェーズC: 運用支援
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools


def create_handover_agent(
    mcp_server_command: str | None = None,
) -> Agent:
    """引き継ぎ（ハンドオーバー）Agentを作成する.

    スタッフの入退社・異動に対応し、事業所設定を更新する。

    Args:
        mcp_server_command: GA-shift MCPサーバーの起動コマンド。

    Returns:
        設定済みのAgno Agent
    """
    ga_mcp = MCPTools(
        command=mcp_server_command or "uv run python -m ga_shift.mcp.server",
    )

    return Agent(
        name="引き継ぎAgent",
        id="handover-agent",
        model=Claude(id="claude-sonnet-4-5-20250929"),
        tools=[ga_mcp],
        instructions=[
            # ── 役割 ──
            "あなたはスタッフの人事異動に対応するエージェントです。",
            "入退社・異動があった場合に、事業所設定を適切に更新し、",
            "影響範囲を報告します。",
            "",
            # ── 対応パターン ──
            "【対応パターン】",
            "",
            "● 新規入社",
            "  1. スタッフ情報の登録（名前、雇用形態、セクション、休日数）",
            "  2. 出勤不可の曜日や制約の設定",
            "  3. 既存の代役ルールへの影響確認",
            "  4. 次回シフト生成時の人数変更の確認",
            "",
            "● 退職",
            "  1. 退職スタッフの制約を確認",
            "  2. 代役ルールの更新（退職者が代役に含まれている場合）",
            "  3. 人員配置基準の再チェック（最低人員を割らないか）",
            "  4. transfer_staff ツールでスタッフ情報を更新",
            "",
            "● セクション異動",
            "  1. 異動元・異動先のセクション人員を確認",
            "  2. キッチン最低人員制約への影響チェック",
            "  3. 制約パラメータの更新",
            "",
            "● 勤務条件変更",
            "  - 正規 ↔ パートの変更",
            "  - 休日数の変更",
            "  - 出勤不可曜日の変更",
            "  - 通院日の変更",
            "",
            # ── ツール使用 ──
            "【ツール使用】",
            "- setup_facility: 事業所設定の更新",
            "- add_constraint: 制約の追加・更新",
            "- transfer_staff: スタッフの追加・削除・情報更新",
            "- check_compliance: 変更後の基準充足チェック",
            "",
            # ── 報告 ──
            "【報告】",
            "- 変更前後の差分を一覧で表示",
            "- 影響を受ける制約をリストアップ",
            "- 次回シフト生成時の注意点を報告",
            "- 必要な追加操作（代役ルール更新等）を提案",
        ],
        markdown=True,
    )
