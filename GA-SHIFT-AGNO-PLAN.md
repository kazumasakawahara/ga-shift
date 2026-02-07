# GA-shift Agno再構成プラン

## 現状分析

### 既存アーキテクチャ（そのまま活かせるもの）

現在のGA-shiftは、すでにエージェントパターンで設計されている。

```
ConductorAgent（パイプライン統制）
  ├── ConstraintBuilderAgent（制約コンパイル）
  ├── GAEngineAgent（GA実行）
  ├── ValidatorAgent（結果検証）
  └── ReporterAgent（レポート生成）
```

GAコア（`engine.py`, `operators.py`, `population.py`, `evaluation.py`）とモデル層（Pydantic v2）は安定しており、テスト52件全パス。これらは**書き換えずにそのまま再利用**する。

### 再構成で変わるもの

| 項目 | Before | After |
|------|--------|-------|
| エージェント基盤 | 自前BaseAgent | Agno Agent |
| LLM連携 | なし | Claude API（Agno経由） |
| 外部アクセス | なし | MCPサーバー |
| UI | CLI / Excel直接 | Streamlit |
| カスタマイズ | コード編集 | 対話で自動生成 |
| メモリ | なし | Agno Memory（事業所設定を記憶） |

---

## 再構成の3フェーズ

### フェーズ1: MCPサーバー化（GAコアのラッピング）

**目的**: 既存のGAエンジンをMCPツールとして公開し、Claudeから呼び出せるようにする。

#### 新規ファイル: `src/ga_shift/mcp/server.py`

```python
from mcp.server import Server
from ga_shift.agents.conductor import ConductorAgent
from ga_shift.io.excel_reader import ExcelReader
from ga_shift.io.template_generator import TemplateGenerator

server = Server("ga-shift")

@server.tool()
async def setup_facility(name: str, sections: list[str],
                         staff: list[dict]) -> dict:
    """事業所の初期設定を行う"""
    ...

@server.tool()
async def add_constraint(constraint_type: str,
                         params: dict) -> dict:
    """制約を追加する（例: 最低人員、代役ルール）"""
    ...

@server.tool()
async def generate_template(year: int, month: int,
                            output_path: str) -> dict:
    """Excelテンプレートを生成する"""
    ...

@server.tool()
async def run_optimization(input_path: str,
                           output_path: str) -> dict:
    """GAを実行し最適シフトを生成する"""
    ...

@server.tool()
async def explain_result(result_path: str) -> dict:
    """生成されたシフトの内容を説明する"""
    ...

@server.tool()
async def adjust_schedule(result_path: str,
                          changes: list[dict]) -> dict:
    """手動でシフトを調整する"""
    ...

@server.tool()
async def check_compliance(result_path: str) -> dict:
    """人員配置基準の充足を確認する"""
    ...
```

#### ディレクトリ構成の変更

```
src/ga_shift/
├── models/          # 既存のまま
├── io/              # 既存のまま
├── constraints/     # 既存のまま
├── ga/              # 既存のまま
├── agents/          # 既存（内部パイプライン用に残す）
└── mcp/             # ★新規
    ├── __init__.py
    ├── server.py    # MCPサーバー本体
    └── tools.py     # ツール定義（serverが大きくなる場合分離）
```

#### このフェーズの成果物
- MCPサーバーとしてGA-shiftが動作する
- Claude Desktop等から`ga-shift`をMCPサーバーとして接続すれば、対話でシフト生成が可能になる
- **既存テスト52件は一切変更なし**

---

### フェーズ2: Agnoエージェント群の構築

**目的**: Agnoフレームワーク上に3つのAIエージェントを構築し、福祉事業所の管理者が対話だけでシフト最適化できるようにする。

#### エージェント構成

```
Streamlit UI
    ↕
┌─────────────────────────────────────────────┐
│  ShiftTeam (Agno Team - coordinate mode)    │
│                                             │
│  ┌─────────────────────────────────┐        │
│  │ HearingAgent（ヒアリング）      │        │
│  │ - 事業所構成を聞き取る          │        │
│  │ - 制約設定を自動生成            │        │
│  │ - ConstraintRegistryへ登録      │        │
│  └─────────────────────────────────┘        │
│                                             │
│  ┌─────────────────────────────────┐        │
│  │ OptimizerAgent（最適化実行）     │        │
│  │ - GA-shift MCPツールを呼び出す  │        │
│  │ - テンプレート生成 → GA実行     │        │
│  └─────────────────────────────────┘        │
│                                             │
│  ┌─────────────────────────────────┐        │
│  │ AdjusterAgent（調整・説明）     │        │
│  │ - 結果をわかりやすく説明        │        │
│  │ - 「○○さんの休みを変えたい」    │        │
│  │   → adjust_schedule呼び出し     │        │
│  │ - 再最適化の判断                │        │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘
```

#### 実装コード概要

```python
# src/ga_shift/agno_agents/hearing.py
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools

class HearingAgent(Agent):
    def __init__(self):
        ga_mcp = MCPTools(
            command="uv",
            args=["run", "python", "-m", "ga_shift.mcp.server"]
        )
        super().__init__(
            name="ヒアリングAgent",
            model=Claude(model="claude-sonnet-4-5-20250929"),
            tools=[ga_mcp],
            instructions=[
                "あなたは福祉事業所のシフト作成を支援するアシスタントです。",
                "まず事業所の基本情報を聞き取ってください：",
                "  - 事業所名、事業種別（B型、A型、生活介護等）",
                "  - スタッフの名前、雇用形態、担当セクション",
                "  - 営業日・営業時間",
                "  - 特別なルール（通院日、代役、最低人員等）",
                "聞き取った情報からsetup_facilityとadd_constraintを呼び出して設定を構築してください。",
                "専門用語は使わず、やさしい日本語で対話してください。"
            ],
            markdown=True
        )
```

```python
# src/ga_shift/agno_agents/optimizer.py
class OptimizerAgent(Agent):
    def __init__(self):
        ga_mcp = MCPTools(...)
        super().__init__(
            name="最適化Agent",
            model=Claude(model="claude-sonnet-4-5-20250929"),
            tools=[ga_mcp],
            instructions=[
                "Excelテンプレートの生成とGA最適化の実行を担当します。",
                "generate_template → ユーザーに希望休入力を依頼 → run_optimization",
                "実行結果のフィットネス値と違反内容を確認し、",
                "品質が低い場合はパラメータを調整して再実行してください。"
            ]
        )
```

```python
# src/ga_shift/agno_agents/adjuster.py
class AdjusterAgent(Agent):
    def __init__(self):
        ga_mcp = MCPTools(...)
        super().__init__(
            name="調整Agent",
            model=Claude(model="claude-sonnet-4-5-20250929"),
            tools=[ga_mcp],
            instructions=[
                "生成されたシフト結果をわかりやすく説明してください。",
                "ユーザーから「○○さんの△日を休みにしたい」等の要望があれば、",
                "adjust_scheduleで調整し、check_complianceで基準充足を確認してください。",
                "調整後に制約違反が発生する場合は、代替案を提示してください。"
            ]
        )
```

```python
# src/ga_shift/agno_agents/team.py
from agno.team import Team

class ShiftTeam(Team):
    def __init__(self):
        super().__init__(
            name="シフト最適化チーム",
            mode="coordinate",
            members=[
                HearingAgent(),
                OptimizerAgent(),
                AdjusterAgent()
            ],
            instructions=[
                "福祉事業所の月次シフト作成を対話的に支援します。",
                "初回はヒアリングAgentが事業所設定を行い、",
                "2回目以降は最適化→調整のフローで進めます。"
            ]
        )
```

#### 新規ディレクトリ

```
src/ga_shift/
├── ...（既存）
├── mcp/              # フェーズ1
└── agno_agents/      # ★フェーズ2
    ├── __init__.py
    ├── hearing.py
    ├── optimizer.py
    ├── adjuster.py
    └── team.py
```

---

### フェーズ3: Streamlit UI + メモリ + 拡張エージェント

**目的**: Webブラウザから使えるUIと、事業所ごとの設定記憶、将来の拡張エージェントを追加する。

#### Streamlit UI

```python
# app.py
import streamlit as st
from ga_shift.agno_agents.team import ShiftTeam

st.set_page_config(page_title="GA-shift", layout="wide")
st.title("シフト自動最適化システム")

team = ShiftTeam()

# チャットUI
if prompt := st.chat_input("シフトについて何でも聞いてください"):
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        response = team.run(prompt)
        st.write(response.content)

# サイドバー: Excel アップロード/ダウンロード
with st.sidebar:
    uploaded = st.file_uploader("希望休Excel", type=["xlsx"])
    if st.button("シフト生成"):
        ...
```

#### Agno Memory（事業所設定の永続化）

```python
from agno.memory.v2.memory import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb

facility_memory = Memory(
    model=Claude(),
    db=SqliteMemoryDb(
        table_name="facility_configs",
        db_file="data/ga_shift_memory.db"
    ),
    memory_types=[
        MemoryType(name="facility_info", description="事業所の基本情報"),
        MemoryType(name="constraint_rules", description="制約ルール"),
        MemoryType(name="past_adjustments", description="過去の手動調整パターン")
    ]
)
```

これにより「先月と同じ設定でお願い」「島村さんの通院日が変わった」といった自然な指示で設定を更新できるようになる。

#### 拡張エージェント候補

| Agent | 役割 | 連携先 |
|-------|------|--------|
| MonitoringAgent | シフト実績の偏り検出・報告 | Excel実績データ |
| ComplianceAgent | 人員配置基準の充足確認 | 法令DB |
| HandoverAgent | 人事異動への対応 | Agno Memory |
| Neo4jBridgeAgent | 利用者通院日→シフト制約自動反映 | support-db MCP |

#### Neo4j連携の具体例

```python
# 利用者の通院スケジュールを制約に自動反映
class Neo4jBridgeAgent(Agent):
    def __init__(self):
        neo4j_mcp = MCPTools(command="uvx", args=["mcp-server-neo4j"])
        ga_mcp = MCPTools(...)
        super().__init__(
            name="Neo4jブリッジ",
            tools=[neo4j_mcp, ga_mcp],
            instructions=[
                "support-dbから利用者の通院スケジュールを取得し、",
                "該当日に同行支援が必要なスタッフの出勤制約を自動設定する。"
            ]
        )
```

---

## 実装ロードマップ

```
フェーズ1（2週間）: MCPサーバー化
  ├─ Week 1: server.py + 7ツール実装
  └─ Week 2: Claude Desktop接続テスト

フェーズ2（3週間）: Agnoエージェント構築
  ├─ Week 3: HearingAgent + テスト
  ├─ Week 4: OptimizerAgent + AdjusterAgent
  └─ Week 5: ShiftTeam統合テスト

フェーズ3（2週間〜）: UI + メモリ + 拡張
  ├─ Week 6: Streamlit UI + Memory
  └─ Week 7+: 拡張エージェント（段階的）
```

## 技術スタック追加分

| 追加ライブラリ | 用途 |
|--------------|------|
| agno | エージェントフレームワーク |
| mcp (fastmcp) | MCPサーバー |
| anthropic | Claude API |
| streamlit | Web UI |
| lancedb | ベクトルDB（知識ベース用） |

## 設計原則

1. **GAコアは触らない**: `ga/`, `models/`, `constraints/`, `io/` はそのまま。テスト52件を壊さない。
2. **MCPが境界**: AgnoエージェントはMCPツール経由でGA機能を呼ぶ。直接importしない。これにより、GAコアとAI層が疎結合になる。
3. **段階的移行**: フェーズ1完了時点でClaude Desktopから使える。フェーズ2以降は付加価値。
4. **mainブランチ汎用性を維持**: Agno関連はkimachiyaブランチに入れるか、別リポジトリ（ga-shift-agno）にする選択肢がある。
