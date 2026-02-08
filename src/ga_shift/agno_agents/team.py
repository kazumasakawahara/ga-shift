"""ShiftTeam - Agentを統括するチーム。

ヒアリング → 最適化 → 調整 のフローを管理する。
enable_neo4j=True にすると Neo4jブリッジAgent が追加され、
support-db からの利用者通院情報を自動でシフト制約に反映できる。
enable_ops=True にすると運用支援Agent群（モニタリング・コンプライアンス・
引き継ぎ）が追加され、生成後のシフト品質管理と人事異動対応を支援する。
enable_extended=True にすると拡張Agent群（レポート・シミュレーション）が追加され、
月次レポート生成とWhat-ifシナリオ分析が可能になる。
Agno Memory を有効にすると、事業所設定を永続化してセッション間で保持できる。
"""

from __future__ import annotations

from pathlib import Path

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.team import Team

from ga_shift.agno_agents.adjuster import create_adjuster_agent
from ga_shift.agno_agents.compliance import create_compliance_agent
from ga_shift.agno_agents.handover import create_handover_agent
from ga_shift.agno_agents.hearing import create_hearing_agent
from ga_shift.agno_agents.monitoring import create_monitoring_agent
from ga_shift.agno_agents.neo4j_bridge import create_neo4j_bridge_agent
from ga_shift.agno_agents.optimizer import create_optimizer_agent
from ga_shift.agno_agents.report import create_report_agent
from ga_shift.agno_agents.simulation import create_simulation_agent

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
    enable_ops: bool = False,
    enable_extended: bool = False,
) -> Team:
    """シフト最適化チームを作成する。

    Args:
        mcp_server_command: MCPサーバーの起動コマンド。
        enable_memory: Agno Memoryを有効にするか。
        memory_db_path: メモリDBのパス（enable_memory=Trueの場合）。
        enable_neo4j: Neo4jブリッジAgentを追加するか。
        neo4j_mcp_command: Neo4j MCPサーバーの起動コマンド。
        enable_ops: 運用支援Agent群を追加するか。
        enable_extended: 拡張Agent群（レポート・シミュレーション）を追加するか。

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

    # Optional: Operations Agents (Phase C)
    if enable_ops:
        monitoring = create_monitoring_agent(mcp_server_command)
        compliance = create_compliance_agent(mcp_server_command)
        handover = create_handover_agent(mcp_server_command)
        members.extend([monitoring, compliance, handover])

    # Optional: Extended Agents (Phase D)
    if enable_extended:
        report = create_report_agent(mcp_server_command)
        simulation = create_simulation_agent(mcp_server_command)
        members.extend([report, simulation])

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

    member_num = 4
    if enable_neo4j:
        base_instructions.append(
            f"{member_num}. Neo4jブリッジAgent: 利用者の通院予定からシフト制約を自動生成"
        )
        member_num += 1

    if enable_ops:
        base_instructions.extend([
            f"{member_num}. モニタリングAgent: シフト結果の公平性分析と偏り検出",
            f"{member_num + 1}. コンプライアンスAgent: 人員配置基準の充足チェック",
            f"{member_num + 2}. 引き継ぎAgent: スタッフの人事異動対応と設定更新",
        ])
        member_num += 3

    if enable_extended:
        base_instructions.extend([
            f"{member_num}. レポートAgent: 月次総合レポートの生成（品質スコア付き）",
            f"{member_num + 1}. シミュレーションAgent: What-ifシナリオの影響分析",
        ])

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

    if enable_ops:
        base_instructions.extend([
            "",
            "● シフト結果の偏り分析・公平性チェック → モニタリングAgent",
            "  例: 「勤務の偏りを確認して」「週末出勤が公平か見て」",
            "",
            "● 人員配置基準・法令遵守チェック → コンプライアンスAgent",
            "  例: 「基準を満たしてるか確認して」「人員配置は大丈夫？」",
            "",
            "● スタッフの入退社・異動・条件変更 → 引き継ぎAgent",
            "  例: 「新しいスタッフが入った」「○○さんが退職する」「セクション異動」",
        ])

    if enable_extended:
        base_instructions.extend([
            "",
            "● 月次レポート・総合評価 → レポートAgent",
            "  例: 「今月のレポートを作って」「シフトの品質評価は？」",
            "",
            "● What-ifシミュレーション → シミュレーションAgent",
            "  例: 「もし○○さんが辞めたら？」「利用者が増えたら？」「パートを増やしたら？」",
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
