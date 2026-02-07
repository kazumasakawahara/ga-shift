"""Neo4jBridgeAgent - support-dbとGA-shiftを橋渡しするエージェント.

Neo4j (support-db) から利用者の通院スケジュールやケア情報を取得し、
該当日に同行支援が必要なスタッフの出勤制約を自動設定する。

フェーズB: Neo4j連携
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools


def create_neo4j_bridge_agent(
    ga_mcp_command: str | None = None,
    neo4j_mcp_command: str | None = None,
) -> Agent:
    """Neo4jブリッジAgentを作成する.

    support-db MCP と ga-shift MCP の両方を持ち、
    利用者情報からシフト制約を自動生成する。

    Args:
        ga_mcp_command: GA-shift MCPサーバーの起動コマンド。
        neo4j_mcp_command: Neo4j support-db MCPサーバーの起動コマンド。

    Returns:
        設定済みのAgno Agent
    """
    # GA-shift MCPツール（制約追加に使用）
    ga_mcp = MCPTools(
        command=ga_mcp_command or "uv run python -m ga_shift.mcp.server",
    )

    # support-db MCPツール（利用者情報の取得に使用）
    neo4j_mcp = MCPTools(
        command=neo4j_mcp_command or "uvx mcp-server-neo4j",
    )

    return Agent(
        name="Neo4jブリッジAgent",
        id="neo4j-bridge-agent",
        model=Claude(id="claude-sonnet-4-5-20250929"),
        tools=[ga_mcp, neo4j_mcp],
        instructions=[
            # ── 役割 ──
            "あなたは利用者支援情報とシフト作成を橋渡しするエージェントです。",
            "support-db（Neo4jグラフデータベース）から利用者の情報を取得し、",
            "シフト作成に必要な制約を自動的に設定します。",
            "",
            # ── 同行支援の自動反映 ──
            "【同行支援の自動反映フロー】",
            "以下の手順で、利用者の通院予定をスタッフのシフト制約に変換します：",
            "",
            "ステップ1: 利用者情報の取得",
            "  - support-dbから利用者(クライアント)一覧を取得",
            "  - 各利用者のプロフィールから通院スケジュールを確認",
            "  - 定期通院（毎週○曜日）と臨時通院を区別",
            "",
            "ステップ2: 同行スタッフの特定",
            "  - 各利用者のキーパーソンや担当スタッフを確認",
            "  - support-dbの支援記録からスタッフの割り当てを取得",
            "  - 同行が必要な通院とそうでないものを判別",
            "",
            "ステップ3: シフト制約への変換",
            "  - 通院同行日 → 該当スタッフの「出勤必須」制約",
            "  - 通院日のスタッフ配置 → 残りのメンバーで最低人員を確保",
            "  - import_accompanied_visits ツールで一括登録",
            "",
            # ── 緊急時の連携 ──
            "【緊急情報の活用】",
            "  - support-dbの緊急情報（NgAction等）を確認",
            "  - 利用者のケア特性に合わせたスタッフ配置を提案",
            "  - 例: パニック対応が得意なスタッフを特定の日に配置",
            "",
            # ── 注意事項 ──
            "- 利用者の個人情報は慎重に扱ってください",
            "- 同行支援の要否が不明な場合は、ユーザーに確認してください",
            "- スタッフ名はGA-shiftの事業所設定と一致する必要があります",
            "- 設定内容をわかりやすく一覧で報告してください",
        ],
        markdown=True,
    )
