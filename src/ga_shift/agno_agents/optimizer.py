"""OptimizerAgent - GAによるシフト最適化を実行する。

Excelテンプレート生成 → 希望休入力依頼 → GA実行 → 品質チェック
のフローを管理する。
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools


def create_optimizer_agent(mcp_server_command: str | None = None) -> Agent:
    """最適化Agentを作成する。

    Args:
        mcp_server_command: MCPサーバーの起動コマンド。

    Returns:
        設定済みのAgno Agent
    """
    ga_mcp = MCPTools(
        command=mcp_server_command or "uv run python -m ga_shift.mcp.server",
    )

    return Agent(
        name="最適化Agent",
        id="optimizer-agent",
        model=Claude(id="claude-sonnet-4-5-20250929"),
        tools=[ga_mcp],
        instructions=[
            # ── 役割 ──
            "あなたはシフト最適化の実行を担当するエージェントです。",
            "",
            # ── フロー ──
            "以下の手順で最適化を進めてください：",
            "",
            "【ステップ1】テンプレート生成",
            "  - generate_shift_template ツールで対象月のExcelテンプレートを生成",
            "  - ユーザーに「テンプレートに希望休（◎）と出勤不可（×）を入力してください」と伝える",
            "  - 生成されたファイルのパスをユーザーに伝える",
            "",
            "【ステップ2】最適化実行",
            "  - ユーザーが入力済みExcelを用意したら、run_optimization を実行",
            "  - デフォルトパラメータ: population_size=100, generations=50",
            "",
            "【ステップ3】品質チェック",
            "  - 結果のbest_scoreとviolationsを確認",
            "  - error_countが0でない場合は、パラメータを調整して再実行を提案",
            "    例: generations=100, population_size=200 に増やす",
            "  - 3回まで再試行可能。それでも改善しない場合はユーザーに報告",
            "",
            "【ステップ4】結果報告",
            "  - 最適化結果をわかりやすく報告",
            "  - 各スタッフの出勤日数、主な制約違反を説明",
            "  - 出力ファイルのパスを伝える",
            "",
            # ── 注意事項 ──
            "- 専門用語（フィットネス値、ペナルティ等）は使わず、",
            "  「スコアが高いほど良いシフトです」のように説明してください。",
            "- エラーがあった場合は、何が問題で、どうすれば解決できるか具体的に伝えてください。",
        ],
        markdown=True,
        # show_tool_calls is not supported in current agno version
    )
