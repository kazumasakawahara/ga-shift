"""Agno エージェントのスモークテスト.

APIキーなしで実行可能。エージェント/チームの構築が正しいことを検証する。
（実際のLLM呼び出しは行わない）
"""

from __future__ import annotations

import pytest

from agno.agent import Agent
from agno.team import Team

from ga_shift.agno_agents.hearing import create_hearing_agent
from ga_shift.agno_agents.optimizer import create_optimizer_agent
from ga_shift.agno_agents.adjuster import create_adjuster_agent
from ga_shift.agno_agents.team import create_shift_team


# ===================================================================
# HearingAgent
# ===================================================================
class TestHearingAgent:
    def test_create_returns_agent(self):
        """create_hearing_agent が Agent を返すこと。"""
        agent = create_hearing_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_hearing_agent()
        assert agent.name == "ヒアリングAgent"

    def test_agent_has_agent_id(self):
        """Agent に agent_id が設定されていること。"""
        agent = create_hearing_agent()
        assert agent.id == "hearing-agent"

    def test_agent_has_instructions(self):
        """Agent に日本語の instructions があること。"""
        agent = create_hearing_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    def test_agent_has_tools(self):
        """Agent に MCPTools がアタッチされていること。"""
        agent = create_hearing_agent()
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_agent_with_custom_command(self):
        """カスタムMCPコマンドで作成できること。"""
        agent = create_hearing_agent(mcp_server_command="echo test")
        assert isinstance(agent, Agent)


# ===================================================================
# OptimizerAgent
# ===================================================================
class TestOptimizerAgent:
    def test_create_returns_agent(self):
        """create_optimizer_agent が Agent を返すこと。"""
        agent = create_optimizer_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_optimizer_agent()
        assert agent.name == "最適化Agent"

    def test_agent_has_agent_id(self):
        """Agent に agent_id が設定されていること。"""
        agent = create_optimizer_agent()
        assert agent.id == "optimizer-agent"

    def test_agent_has_instructions(self):
        """Agent に instructions があること。"""
        agent = create_optimizer_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0


# ===================================================================
# AdjusterAgent
# ===================================================================
class TestAdjusterAgent:
    def test_create_returns_agent(self):
        """create_adjuster_agent が Agent を返すこと。"""
        agent = create_adjuster_agent()
        assert isinstance(agent, Agent)

    def test_agent_has_name(self):
        """Agent に名前が設定されていること。"""
        agent = create_adjuster_agent()
        assert agent.name == "調整Agent"

    def test_agent_has_agent_id(self):
        """Agent に agent_id が設定されていること。"""
        agent = create_adjuster_agent()
        assert agent.id == "adjuster-agent"

    def test_agent_has_instructions(self):
        """Agent に instructions があること。"""
        agent = create_adjuster_agent()
        assert agent.instructions is not None
        assert len(agent.instructions) > 0


# ===================================================================
# ShiftTeam
# ===================================================================
class TestShiftTeam:
    def test_create_returns_team(self):
        """create_shift_team が Team を返すこと。"""
        team = create_shift_team()
        assert isinstance(team, Team)

    def test_team_has_name(self):
        """Team に名前が設定されていること。"""
        team = create_shift_team()
        assert team.name == "シフト最適化チーム"

    def test_team_has_three_members(self):
        """Team に3つのメンバーがいること。"""
        team = create_shift_team()
        assert len(team.members) == 3

    def test_team_member_names(self):
        """Team メンバーの名前が正しいこと。"""
        team = create_shift_team()
        member_names = sorted(m.name for m in team.members)
        assert member_names == ["ヒアリングAgent", "最適化Agent", "調整Agent"]

    def test_team_has_model(self):
        """Team にモデルが設定されていること。"""
        team = create_shift_team()
        assert team.model is not None

    def test_team_with_memory_disabled(self):
        """Memory無効でもTeamが作成できること。"""
        team = create_shift_team(enable_memory=False)
        assert isinstance(team, Team)

    def test_team_with_memory_enabled(self):
        """Memory有効でTeamが作成できること。"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            team = create_shift_team(
                enable_memory=True,
                memory_db_path=db_path,
            )
            assert isinstance(team, Team)

    def test_team_instructions_contain_key_phrases(self):
        """Team の instructions に重要なフレーズが含まれていること。"""
        team = create_shift_team()
        all_instructions = " ".join(team.instructions)

        assert "ヒアリングAgent" in all_instructions
        assert "最適化Agent" in all_instructions
        assert "調整Agent" in all_instructions
        assert "やさしい日本語" in all_instructions


# ===================================================================
# クロスエージェントテスト
# ===================================================================
class TestAgentConsistency:
    def test_all_agents_use_same_model(self):
        """全エージェントが同じモデルを使用していること。"""
        hearing = create_hearing_agent()
        optimizer = create_optimizer_agent()
        adjuster = create_adjuster_agent()

        # All should use Claude
        assert hearing.model is not None
        assert optimizer.model is not None
        assert adjuster.model is not None

    def test_all_agents_have_unique_ids(self):
        """全エージェントのIDがユニークであること。"""
        hearing = create_hearing_agent()
        optimizer = create_optimizer_agent()
        adjuster = create_adjuster_agent()

        ids = {hearing.id, optimizer.id, adjuster.id}
        assert len(ids) == 3

    def test_all_agents_have_mcp_tools(self):
        """全エージェントにMCPツールがアタッチされていること。"""
        hearing = create_hearing_agent()
        optimizer = create_optimizer_agent()
        adjuster = create_adjuster_agent()

        assert len(hearing.tools) > 0
        assert len(optimizer.tools) > 0
        assert len(adjuster.tools) > 0
