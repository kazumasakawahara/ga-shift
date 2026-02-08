"""Neo4jBridgeAgent のスモークテスト.

APIキーなしで実行可能。エージェント構築が正しいことを検証する。
（実際のLLM呼び出しやNeo4j接続は行わない）
"""

from __future__ import annotations

import pytest

from agno.agent import Agent
from agno.team import Team

from ga_shift.agno_agents.neo4j_bridge import create_neo4j_bridge_agent
from ga_shift.agno_agents.team import create_shift_team


# ===================================================================
# Neo4jBridgeAgent
# ===================================================================
class TestNeo4jBridgeAgent:
    def test_create_returns_agent(self):
        """create_neo4j_bridge_agent が Agent を返すこと。"""
        agent = create_neo4j_bridge_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_neo4j_bridge_agent()
        assert agent.name == "Neo4jブリッジAgent"

    def test_agent_has_agent_id(self):
        """Agent に id が設定されていること。"""
        agent = create_neo4j_bridge_agent()
        assert agent.id == "neo4j-bridge-agent"

    def test_agent_has_instructions(self):
        """Agent に日本語の instructions があること。"""
        agent = create_neo4j_bridge_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    def test_agent_has_two_mcp_tools(self):
        """Agent に2つのMCPTools（ga-shift + neo4j）がアタッチされていること。"""
        agent = create_neo4j_bridge_agent()
        assert agent.tools is not None
        assert len(agent.tools) == 2

    def test_agent_with_custom_commands(self):
        """カスタムMCPコマンドで作成できること。"""
        agent = create_neo4j_bridge_agent(
            ga_mcp_command="echo test-ga",
            neo4j_mcp_command="echo test-neo4j",
        )
        assert isinstance(agent, Agent)

    def test_agent_has_model(self):
        """Agent にモデルが設定されていること。"""
        agent = create_neo4j_bridge_agent()
        assert agent.model is not None

    def test_instructions_mention_support_db(self):
        """instructions に support-db 関連のフレーズがあること。"""
        agent = create_neo4j_bridge_agent()
        all_instructions = " ".join(agent.instructions)
        assert "support-db" in all_instructions

    def test_instructions_mention_accompanied_visits(self):
        """instructions に通院同行関連のフレーズがあること。"""
        agent = create_neo4j_bridge_agent()
        all_instructions = " ".join(agent.instructions)
        assert "通院" in all_instructions

    def test_instructions_mention_constraint(self):
        """instructions にシフト制約関連のフレーズがあること。"""
        agent = create_neo4j_bridge_agent()
        all_instructions = " ".join(agent.instructions)
        assert "制約" in all_instructions


# ===================================================================
# ShiftTeam with Neo4j
# ===================================================================
class TestShiftTeamWithNeo4j:
    def test_team_without_neo4j_has_three_members(self):
        """Neo4j無効時は3つのメンバーのみ。"""
        team = create_shift_team(enable_neo4j=False)
        assert len(team.members) == 3

    def test_team_with_neo4j_has_four_members(self):
        """Neo4j有効時は4つのメンバーになること。"""
        team = create_shift_team(enable_neo4j=True)
        assert len(team.members) == 4

    def test_team_with_neo4j_member_names(self):
        """Neo4j有効時のメンバー名が正しいこと。"""
        team = create_shift_team(enable_neo4j=True)
        member_names = sorted(m.name for m in team.members)
        assert member_names == [
            "Neo4jブリッジAgent",
            "ヒアリングAgent",
            "最適化Agent",
            "調整Agent",
        ]

    def test_team_with_neo4j_instructions_mention_bridge(self):
        """Neo4j有効時のinstructionsにブリッジAgentの記載があること。"""
        team = create_shift_team(enable_neo4j=True)
        all_instructions = " ".join(team.instructions)
        assert "Neo4jブリッジAgent" in all_instructions

    def test_team_without_neo4j_instructions_no_bridge(self):
        """Neo4j無効時のinstructionsにブリッジAgentの記載がないこと。"""
        team = create_shift_team(enable_neo4j=False)
        all_instructions = " ".join(team.instructions)
        assert "Neo4jブリッジAgent" not in all_instructions

    def test_team_with_neo4j_returns_team(self):
        """Neo4j有効でTeamが返ること。"""
        team = create_shift_team(enable_neo4j=True)
        assert isinstance(team, Team)

    def test_team_with_neo4j_custom_command(self):
        """カスタムNeo4j MCPコマンドでTeamが作成できること。"""
        team = create_shift_team(
            enable_neo4j=True,
            neo4j_mcp_command="echo test-neo4j",
        )
        assert isinstance(team, Team)
        assert len(team.members) == 4


# ===================================================================
# クロスエージェントテスト (Neo4j含む)
# ===================================================================
class TestAgentConsistencyWithNeo4j:
    def test_all_agents_have_unique_ids_with_neo4j(self):
        """Neo4j有効時の全エージェントIDがユニークであること。"""
        team = create_shift_team(enable_neo4j=True)
        ids = {m.id for m in team.members}
        assert len(ids) == 4

    def test_neo4j_bridge_id_is_unique(self):
        """Neo4jブリッジAgentのIDが他と重複しないこと。"""
        agent = create_neo4j_bridge_agent()
        from ga_shift.agno_agents.hearing import create_hearing_agent
        from ga_shift.agno_agents.optimizer import create_optimizer_agent
        from ga_shift.agno_agents.adjuster import create_adjuster_agent

        hearing = create_hearing_agent()
        optimizer = create_optimizer_agent()
        adjuster = create_adjuster_agent()

        ids = {agent.id, hearing.id, optimizer.id, adjuster.id}
        assert len(ids) == 4
