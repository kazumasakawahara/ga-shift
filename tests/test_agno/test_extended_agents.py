"""拡張Agent群（フェーズD）のスモークテスト.

ReportAgent, SimulationAgent の構築と
enable_extended=True 時の Team 統合を検証する。
"""

from __future__ import annotations

import pytest

from agno.agent import Agent
from agno.team import Team

from ga_shift.agno_agents.report import create_report_agent
from ga_shift.agno_agents.simulation import create_simulation_agent
from ga_shift.agno_agents.team import create_shift_team


# ===================================================================
# ReportAgent
# ===================================================================
class TestReportAgent:
    def test_create_returns_agent(self):
        """create_report_agent が Agent を返すこと。"""
        agent = create_report_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_report_agent()
        assert agent.name == "レポートAgent"

    def test_agent_has_id(self):
        """Agent に id が設定されていること。"""
        agent = create_report_agent()
        assert agent.id == "report-agent"

    def test_agent_has_instructions(self):
        """Agent に日本語の instructions があること。"""
        agent = create_report_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    def test_agent_has_tools(self):
        """Agent に MCPTools がアタッチされていること。"""
        agent = create_report_agent()
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_agent_with_custom_command(self):
        """カスタムMCPコマンドで作成できること。"""
        agent = create_report_agent(mcp_server_command="echo test")
        assert isinstance(agent, Agent)

    def test_instructions_mention_report(self):
        """instructions にレポート生成に関する記述があること。"""
        agent = create_report_agent()
        all_instr = " ".join(agent.instructions)
        assert "レポート" in all_instr

    def test_instructions_mention_generate_shift_report(self):
        """instructions に generate_shift_report ツールの記述があること。"""
        agent = create_report_agent()
        all_instr = " ".join(agent.instructions)
        assert "generate_shift_report" in all_instr


# ===================================================================
# SimulationAgent
# ===================================================================
class TestSimulationAgent:
    def test_create_returns_agent(self):
        """create_simulation_agent が Agent を返すこと。"""
        agent = create_simulation_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_simulation_agent()
        assert agent.name == "シミュレーションAgent"

    def test_agent_has_id(self):
        """Agent に id が設定されていること。"""
        agent = create_simulation_agent()
        assert agent.id == "simulation-agent"

    def test_agent_has_instructions(self):
        """Agent に instructions があること。"""
        agent = create_simulation_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    def test_agent_has_tools(self):
        """Agent に MCPTools がアタッチされていること。"""
        agent = create_simulation_agent()
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_agent_with_custom_command(self):
        """カスタムMCPコマンドで作成できること。"""
        agent = create_simulation_agent(mcp_server_command="echo test")
        assert isinstance(agent, Agent)

    def test_instructions_mention_scenario(self):
        """instructions にシナリオシミュレーションに関する記述があること。"""
        agent = create_simulation_agent()
        all_instr = " ".join(agent.instructions)
        assert "シナリオ" in all_instr or "simulate" in all_instr.lower()

    def test_instructions_mention_simulate_scenario(self):
        """instructions に simulate_scenario ツールの記述があること。"""
        agent = create_simulation_agent()
        all_instr = " ".join(agent.instructions)
        assert "simulate_scenario" in all_instr


# ===================================================================
# ShiftTeam with extended agents
# ===================================================================
class TestShiftTeamWithExtended:
    def test_team_without_extended(self):
        """enable_extended=False で3メンバーのTeamが作成されること。"""
        team = create_shift_team(enable_extended=False)
        assert len(team.members) == 3

    def test_team_with_extended(self):
        """enable_extended=True で5メンバーのTeamが作成されること。"""
        team = create_shift_team(enable_extended=True)
        assert len(team.members) == 5

    def test_team_with_extended_member_names(self):
        """enable_extended=True のメンバー名が正しいこと。"""
        team = create_shift_team(enable_extended=True)
        member_names = sorted(m.name for m in team.members)
        assert member_names == [
            "シミュレーションAgent",
            "ヒアリングAgent",
            "レポートAgent",
            "最適化Agent",
            "調整Agent",
        ]

    def test_team_with_extended_returns_team(self):
        """enable_extended=True でも Team を返すこと。"""
        team = create_shift_team(enable_extended=True)
        assert isinstance(team, Team)

    def test_team_with_extended_instructions(self):
        """enable_extended=True の instructions にレポート・シミュレーション関連のルーティングがあること。"""
        team = create_shift_team(enable_extended=True)
        all_instr = " ".join(team.instructions)
        assert "レポートAgent" in all_instr
        assert "シミュレーションAgent" in all_instr

    def test_team_without_extended_no_extended_instructions(self):
        """enable_extended=False の instructions に拡張Agent記述がないこと。"""
        team = create_shift_team(enable_extended=False)
        all_instr = " ".join(team.instructions)
        assert "レポートAgent" not in all_instr
        assert "シミュレーションAgent" not in all_instr

    def test_team_with_all_options(self):
        """全オプション有効時に9メンバーになること。"""
        team = create_shift_team(
            enable_neo4j=True,
            enable_ops=True,
            enable_extended=True,
        )
        assert len(team.members) == 9

    def test_team_with_all_options_member_names(self):
        """全オプション有効時のメンバー名が正しいこと。"""
        team = create_shift_team(
            enable_neo4j=True,
            enable_ops=True,
            enable_extended=True,
        )
        member_names = sorted(m.name for m in team.members)
        assert member_names == [
            "Neo4jブリッジAgent",
            "コンプライアンスAgent",
            "シミュレーションAgent",
            "ヒアリングAgent",
            "モニタリングAgent",
            "レポートAgent",
            "引き継ぎAgent",
            "最適化Agent",
            "調整Agent",
        ]

    def test_team_with_all_options_instructions(self):
        """全オプション有効時に全メンバーのルーティングがあること。"""
        team = create_shift_team(
            enable_neo4j=True,
            enable_ops=True,
            enable_extended=True,
        )
        all_instr = " ".join(team.instructions)
        assert "Neo4jブリッジAgent" in all_instr
        assert "モニタリングAgent" in all_instr
        assert "レポートAgent" in all_instr
        assert "シミュレーションAgent" in all_instr

    def test_team_ops_and_extended(self):
        """enable_ops=True + enable_extended=True で8メンバーになること。"""
        team = create_shift_team(enable_ops=True, enable_extended=True)
        assert len(team.members) == 8


# ===================================================================
# クロスエージェントテスト（拡張Agent群）
# ===================================================================
class TestExtendedAgentConsistency:
    def test_all_extended_agents_have_unique_ids(self):
        """拡張Agent群のIDがすべてユニークであること。"""
        report = create_report_agent()
        simulation = create_simulation_agent()
        ids = {report.id, simulation.id}
        assert len(ids) == 2

    def test_all_agents_have_unique_ids_with_all(self):
        """全Agent（コア + neo4j + 運用 + 拡張）のIDがすべてユニークであること。"""
        team = create_shift_team(
            enable_neo4j=True,
            enable_ops=True,
            enable_extended=True,
        )
        ids = [m.id for m in team.members]
        assert len(ids) == len(set(ids))

    def test_all_extended_agents_have_model(self):
        """拡張Agent群すべてにモデルが設定されていること。"""
        report = create_report_agent()
        simulation = create_simulation_agent()
        assert report.model is not None
        assert simulation.model is not None
