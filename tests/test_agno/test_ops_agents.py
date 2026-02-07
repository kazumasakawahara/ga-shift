"""運用支援Agent群（フェーズC）のスモークテスト.

MonitoringAgent, ComplianceAgent, HandoverAgent の構築と
enable_ops=True 時の Team 統合を検証する。
"""

from __future__ import annotations

import pytest

from agno.agent import Agent
from agno.team import Team

from ga_shift.agno_agents.monitoring import create_monitoring_agent
from ga_shift.agno_agents.compliance import create_compliance_agent
from ga_shift.agno_agents.handover import create_handover_agent
from ga_shift.agno_agents.team import create_shift_team


# ===================================================================
# MonitoringAgent
# ===================================================================
class TestMonitoringAgent:
    def test_create_returns_agent(self):
        """create_monitoring_agent が Agent を返すこと。"""
        agent = create_monitoring_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_monitoring_agent()
        assert agent.name == "モニタリングAgent"

    def test_agent_has_id(self):
        """Agent に id が設定されていること。"""
        agent = create_monitoring_agent()
        assert agent.id == "monitoring-agent"

    def test_agent_has_instructions(self):
        """Agent に日本語の instructions があること。"""
        agent = create_monitoring_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    def test_agent_has_tools(self):
        """Agent に MCPTools がアタッチされていること。"""
        agent = create_monitoring_agent()
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_agent_with_custom_command(self):
        """カスタムMCPコマンドで作成できること。"""
        agent = create_monitoring_agent(mcp_server_command="echo test")
        assert isinstance(agent, Agent)

    def test_instructions_mention_fairness(self):
        """instructions に公平性分析に関する記述があること。"""
        agent = create_monitoring_agent()
        all_instr = " ".join(agent.instructions)
        assert "公平性" in all_instr or "偏り" in all_instr

    def test_instructions_mention_consecutive(self):
        """instructions に連続勤務に関する記述があること。"""
        agent = create_monitoring_agent()
        all_instr = " ".join(agent.instructions)
        assert "連続勤務" in all_instr


# ===================================================================
# ComplianceAgent
# ===================================================================
class TestComplianceAgent:
    def test_create_returns_agent(self):
        """create_compliance_agent が Agent を返すこと。"""
        agent = create_compliance_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_compliance_agent()
        assert agent.name == "コンプライアンスAgent"

    def test_agent_has_id(self):
        """Agent に id が設定されていること。"""
        agent = create_compliance_agent()
        assert agent.id == "compliance-agent"

    def test_agent_has_instructions(self):
        """Agent に instructions があること。"""
        agent = create_compliance_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    def test_agent_has_tools(self):
        """Agent に MCPTools がアタッチされていること。"""
        agent = create_compliance_agent()
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_agent_with_custom_command(self):
        """カスタムMCPコマンドで作成できること。"""
        agent = create_compliance_agent(mcp_server_command="echo test")
        assert isinstance(agent, Agent)

    def test_instructions_mention_staffing_standards(self):
        """instructions に人員配置基準に関する記述があること。"""
        agent = create_compliance_agent()
        all_instr = " ".join(agent.instructions)
        assert "人員配置" in all_instr

    def test_instructions_mention_b_type(self):
        """instructions に就労継続支援B型に関する記述があること。"""
        agent = create_compliance_agent()
        all_instr = " ".join(agent.instructions)
        assert "就労継続支援B型" in all_instr


# ===================================================================
# HandoverAgent
# ===================================================================
class TestHandoverAgent:
    def test_create_returns_agent(self):
        """create_handover_agent が Agent を返すこと。"""
        agent = create_handover_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_handover_agent()
        assert agent.name == "引き継ぎAgent"

    def test_agent_has_id(self):
        """Agent に id が設定されていること。"""
        agent = create_handover_agent()
        assert agent.id == "handover-agent"

    def test_agent_has_instructions(self):
        """Agent に instructions があること。"""
        agent = create_handover_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    def test_agent_has_tools(self):
        """Agent に MCPTools がアタッチされていること。"""
        agent = create_handover_agent()
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_agent_with_custom_command(self):
        """カスタムMCPコマンドで作成できること。"""
        agent = create_handover_agent(mcp_server_command="echo test")
        assert isinstance(agent, Agent)

    def test_instructions_mention_transfer(self):
        """instructions に人事異動に関する記述があること。"""
        agent = create_handover_agent()
        all_instr = " ".join(agent.instructions)
        assert "入退社" in all_instr or "異動" in all_instr

    def test_instructions_mention_transfer_staff(self):
        """instructions に transfer_staff ツールの記述があること。"""
        agent = create_handover_agent()
        all_instr = " ".join(agent.instructions)
        assert "transfer_staff" in all_instr


# ===================================================================
# ShiftTeam with ops agents
# ===================================================================
class TestShiftTeamWithOps:
    def test_team_without_ops(self):
        """enable_ops=False で3メンバーのTeamが作成されること。"""
        team = create_shift_team(enable_ops=False)
        assert len(team.members) == 3

    def test_team_with_ops(self):
        """enable_ops=True で6メンバーのTeamが作成されること。"""
        team = create_shift_team(enable_ops=True)
        assert len(team.members) == 6

    def test_team_with_ops_member_names(self):
        """enable_ops=True のメンバー名が正しいこと。"""
        team = create_shift_team(enable_ops=True)
        member_names = sorted(m.name for m in team.members)
        assert member_names == [
            "コンプライアンスAgent",
            "ヒアリングAgent",
            "モニタリングAgent",
            "引き継ぎAgent",
            "最適化Agent",
            "調整Agent",
        ]

    def test_team_with_ops_returns_team(self):
        """enable_ops=True でも Team を返すこと。"""
        team = create_shift_team(enable_ops=True)
        assert isinstance(team, Team)

    def test_team_with_ops_instructions(self):
        """enable_ops=True の instructions にモニタリング関連のルーティングがあること。"""
        team = create_shift_team(enable_ops=True)
        all_instr = " ".join(team.instructions)
        assert "モニタリングAgent" in all_instr
        assert "コンプライアンスAgent" in all_instr
        assert "引き継ぎAgent" in all_instr

    def test_team_without_ops_no_ops_instructions(self):
        """enable_ops=False の instructions に運用Agent記述がないこと。"""
        team = create_shift_team(enable_ops=False)
        all_instr = " ".join(team.instructions)
        assert "モニタリングAgent" not in all_instr
        assert "コンプライアンスAgent" not in all_instr
        assert "引き継ぎAgent" not in all_instr

    def test_team_with_both_neo4j_and_ops(self):
        """enable_neo4j=True + enable_ops=True で7メンバーになること。"""
        team = create_shift_team(enable_neo4j=True, enable_ops=True)
        assert len(team.members) == 7

    def test_team_with_both_instructions(self):
        """両方有効時に全メンバーのルーティングがあること。"""
        team = create_shift_team(enable_neo4j=True, enable_ops=True)
        all_instr = " ".join(team.instructions)
        assert "Neo4jブリッジAgent" in all_instr
        assert "モニタリングAgent" in all_instr
        assert "引き継ぎAgent" in all_instr


# ===================================================================
# クロスエージェントテスト（運用Agent群）
# ===================================================================
class TestOpsAgentConsistency:
    def test_all_ops_agents_have_unique_ids(self):
        """運用Agent群のIDがすべてユニークであること。"""
        monitoring = create_monitoring_agent()
        compliance = create_compliance_agent()
        handover = create_handover_agent()
        ids = {monitoring.id, compliance.id, handover.id}
        assert len(ids) == 3

    def test_all_agents_have_unique_ids_with_core(self):
        """全Agent（コア + 運用）のIDがすべてユニークであること。"""
        team = create_shift_team(enable_ops=True)
        ids = [m.id for m in team.members]
        assert len(ids) == len(set(ids))

    def test_all_ops_agents_have_model(self):
        """運用Agent群すべてにモデルが設定されていること。"""
        monitoring = create_monitoring_agent()
        compliance = create_compliance_agent()
        handover = create_handover_agent()
        assert monitoring.model is not None
        assert compliance.model is not None
        assert handover.model is not None
