"""ShiftTeam - Agentを統括するチーム。

ヒアリング → 最適化 → 調整 のフローを管理する。
enable_neo4j=True にすると Neo4jブリッジAgent が追加され、
support-db からの利用者通院情報を自動でシフト制約に反映できる。
Agno Memory を有効にすると、事業所設定を永続化してセッション間で保持できる。
"""

from __future__ import annotations

from pathlib import Path

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.team import Team

from ga_shift.agno_agents.adjuster import create_adjuster_agent
from ga_shift.agno_agents.hearing import create_hearing_agent
from ga_shift.agno_agents.neo4j_bridge import create_neo4j_bridge_agent
from ga_shift.agno_agents.optimizer import create_optimizer_agent

# ---------------------------------------------------------------------------
# Memory DB default path
# ---------------------------------------------------------------------------
_DEFAULT_MEMORY_DB = "data/ga_shift_memory.db"


def create_shift_team(
    mcp_server_command: str | None = None,
    enable_memory: bool = False,
    memory_db_path: str | None = None,
    enable_neo4j: bool = False,
    neo4j_mcp_command: str | None = None,
) -> Team:
    """シフト最適化チームを作成する。

    Args:
        mcp_server_command: MCPサーバーの起動コマンド。
        enable_memory: Agno Memoryを有効にするか。
        memory_db_path: メモリDBのパス（enable_memory=Trueの場合）。
        enable_neo4j: Neo4jブリッジAgentを追加するか。
        neo4j_mcp_command: Neo4j MCPサーバーの起動コマンド。

    Returns:
        設定済みのAgno Team
    """
    hearing = create_hearing_agent(mcp_server_command)
    optimizer = create_optimizer_agent(mcp_server_command)
    adjuster = create_adjuster_agent(mcp_server_command)

    # Optional: Neo4j Bridge Agent
    members: list[Agent] = [hearing, optimizer, adjuster]
    if enable_neo4j:
        neo4j_bridge = create_neo4j_bridge_agent(
            ga_mcp_command=mcp_server_command,
            neo4j_mcp_command=neo4j_mcp_command,
        )
        members.append(neo4j_bridge)

    # --- Memory configuration ---
    db = None
    if enable_memory:
        try:
            from agno.db.sqlite import SqliteDb

            db_path = memory_db_path or _DEFAULT_MEMORY_DB
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            db = SqliteDb(db_file=db_path)
        except ImportError:
            # agno.db.sqlite が利用できない場合は Memory なしで続行
            pass

    # --- Build instructions ---
    base_instructions = [
        "あなたは福祉事業所の月次シフト作成を対話的に支援するチームのリーダーです。",
        "",
        "【メンバー】",
        "1. ヒアリングAgent: 事業所の情報収集と設定を担当",
        "2. 最適化Agent: Excelテンプレート生成とGA最適化の実行を担当",
        "3. 調整Agent: 結果の説明と手動調整を担当",
    ]

    if enable_neo4j:
        base_instructions.append(
            "4. Neo4jブリッジAgent: 利用者の通院予定からシフト制約を自動生成"
        )

    base_instructions.extend([
        "",
        "【フロー判定】",
        "ユーザーの発言内容に応じて、適切なメンバーにタスクを割り振ってください：",
        "",
        "● 初回 or 事業所設定に関する質問 → ヒアリングAgent",
        "  例: 「新しい事業所を設定したい」「スタッフが変わった」",
        "",
        "● テンプレート生成 or 最適化実行 → 最適化Agent",
        "  例: 「来月のシフトを作って」「テンプレートを作りたい」",
        "",
        "● 結果の確認 or 手動調整 → 調整Agent",
        "  例: 「結果を見せて」「○○さんの休みを変えたい」",
    ])

    if enable_neo4j:
        base_instructions.extend([
            "",
            "● 利用者の通院情報 or support-db連携 → Neo4jブリッジAgent",
            "  例: 「利用者の通院予定を反映して」「support-dbから制約を取り込みたい」",
        ])

    base_instructions.extend([
        "",
        "● 複合的な質問 → 適切に分割して複数のメンバーに依頼",
        "",
        "【メモリ機能】",
        "- 事業所情報やスタッフ構成は記憶されます。",
        "- 「先月と同じ設定で」「島村さんの通院日が水曜から木曜に変わった」",
        "  といった自然な指示で設定を更新できます。",
        "",
        "【注意事項】",
        "- ユーザーにはチームの内部構造を見せない（「ヒアリングAgentに聞きます」等は不要）",
        "- 自然な対話として応答してください",
        "- 専門用語は避け、やさしい日本語で対話してください",
    ])

    team = Team(
        name="シフト最適化チーム",
        members=members,
        model=Claude(id="claude-sonnet-4-5-20250929"),
        instructions=base_instructions,
        markdown=True,
        # --- Memory ---
        **({"db": db, "enable_user_memories": True} if db else {}),
    )

    return team
