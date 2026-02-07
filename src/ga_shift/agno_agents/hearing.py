"""HearingAgent - 事業所の構成をヒアリングし、制約設定を自動生成する。

対話を通じて事業所の基本情報（スタッフ構成、セクション、特別ルール等）を
聞き取り、GA-shift MCPツールを使って設定を構築する。
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools


def create_hearing_agent(mcp_server_command: str | None = None) -> Agent:
    """ヒアリングAgentを作成する。

    Args:
        mcp_server_command: MCPサーバーの起動コマンド。
            Noneの場合はデフォルトのga-shift MCPサーバーを使用。

    Returns:
        設定済みのAgno Agent
    """
    # GA-shift MCPツール
    ga_mcp = MCPTools(
        command=mcp_server_command or "uv",
        args=["run", "python", "-m", "ga_shift.mcp.server"],
    )

    return Agent(
        name="ヒアリングAgent",
        agent_id="hearing-agent",
        model=Claude(model="claude-sonnet-4-5-20250929"),
        tools=[ga_mcp],
        instructions=[
            # ── 役割 ──
            "あなたは福祉事業所のシフト作成を支援するアシスタントです。",
            "プログラミングの知識がない管理者でも使えるよう、やさしい日本語で対話してください。",
            "",
            # ── ヒアリングの流れ ──
            "以下の順番で事業所の情報を聞き取ってください：",
            "",
            "【ステップ1】事業所の基本情報",
            "  - 事業所名",
            "  - 事業種別（就労継続支援B型、A型、生活介護 など）",
            "  - 営業日・営業時間（平日のみ？土曜も？）",
            "",
            "【ステップ2】スタッフ情報",
            "  - 各スタッフの名前",
            "  - 雇用形態（正規 or パート）",
            "  - 担当セクション（仕込み、ランチ、ホール 等）",
            "  - 有給残日数",
            "  - 毎月の休日数",
            "  - 固定の出勤不可曜日（例：毎週水曜通院）",
            "",
            "【ステップ3】シフトルール",
            "  - 1日の最低必要人数",
            "  - セクションごとの最低人数（キッチン最低3人 等）",
            "  - 代役ルール（○○さんが休みの時は△△さんが入る 等）",
            "  - その他の特別ルール",
            "",
            # ── ツール使用 ──
            "聞き取りが完了したら、以下のMCPツールを順番に呼び出してください：",
            "1. setup_facility: 事業所の初期設定",
            "2. add_constraint: 聞き取ったルールごとに制約を追加",
            "",
            # ── 注意事項 ──
            "- 一度にすべてを聞かず、ステップごとに確認しながら進めてください。",
            "- ユーザーが曖昧な表現をした場合は、具体例を示して確認してください。",
            "- 設定が完了したら、内容をわかりやすくまとめて確認を取ってください。",
        ],
        markdown=True,
        show_tool_calls=True,
    )
