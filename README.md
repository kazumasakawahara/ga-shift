# GA-Shift: シフト表自動作成システム

遺伝的アルゴリズム（GA）× AIエージェント（Agno）× MCP による、シフト表自動作成システムです。
福祉事業所（就労継続支援B型等）の月次スタッフシフトを、対話形式で自動生成します。

## 特徴

- **遺伝的アルゴリズム** — 一様交叉・突然変異・エリート保存による最適化で、制約を満たすシフト表を自動生成
- **14種類の制約テンプレート** — 連勤上限、公平性確保、キッチン最低人員など、プラグイン方式で自由にカスタマイズ
- **MCP（Model Context Protocol）サーバー** — GAエンジンを15のツールとしてラップし、AIアシスタント（Claude Desktop等）から直接操作可能
- **Agno AIエージェントチーム（最大9 Agent）** — ヒアリング → 最適化 → 調整を軸に、Neo4j連携・運用支援・レポート・シミュレーションまで対話的に支援
- **2種類のUI** — タブ式Web UI（従来型）とチャット式AI UI（Agno統合型）を選択可能
- **Excel入出力** — 既存の勤務表Excelをそのまま入力し、結果もExcelで出力
- **270テスト** — 制約・GA・IO・MCP・Agno全レイヤーの包括的テストスイート

## アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│  Streamlit Chat UI  /  Claude Desktop            │  ← ユーザー接点
└──────────────┬──────────────────┬────────────────┘
               │                 │
    ┌──────────▼──────────────┐  │
    │  Agno ShiftTeam (max 9) │  │
    │  ├ HearingAgent         │  │
    │  ├ OptimizerAgent       │  │
    │  ├ AdjusterAgent        │  │
    │  ├ Neo4jBridgeAgent  [B]│  │
    │  ├ MonitoringAgent   [C]│  │
    │  ├ ComplianceAgent   [C]│  │
    │  ├ HandoverAgent     [C]│  │
    │  ├ ReportAgent       [D]│  │
    │  └ SimulationAgent   [D]│  │
    └──────────┬──────────────┘  │
               │ MCPTools        │ MCP Protocol
    ┌──────────▼─────────────────▼────────────────┐
    │  FastMCP Server (15 tools)                   │  ← 境界層
    └──────────────────┬──────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────┐
    │  GA Core (変更なし)                          │
    │  ├ models/   — Pydantic データモデル         │
    │  ├ ga/       — GAエンジン                    │
    │  ├ constraints/ — 制約レジストリ             │
    │  └ io/       — Excel入出力                   │
    └─────────────────────────────────────────────┘
              ↕                         ↕
    ┌─────────────────┐       ┌────────────────┐
    │  Neo4j           │       │  Excel ファイル  │
    │  support-db [B]  │       │                │
    └─────────────────┘       └────────────────┘
```

**設計原則**: GAコア（`models/`, `ga/`, `constraints/`, `io/`）は一切変更しない。MCPサーバーが境界層となり、Agnoエージェントは必ずMCPツール経由でGAコアを操作する。

## クイックスタート

```bash
# 1. リポジトリ取得
git clone https://github.com/kazumasakawahara/ga-shift.git
cd ga-shift

# 2. 依存関係のインストール（uvを使用）
uv sync
uv pip install -e ".[agno]"    # Agno + MCP を使う場合

# 3. テスト実行（270件）
uv run pytest tests/ -q

# 4. UI起動（いずれか）
uv run streamlit run src/ga_shift/ui/app.py       # タブ式UI
uv run streamlit run src/ga_shift/ui/chat_app.py   # チャット式AI UI
```

ブラウザで `http://localhost:8501` を開いてください。

> 詳しいセットアップ手順は [SETUP_GUIDE.md](SETUP_GUIDE.md) を参照してください。

## Claude Desktop 設定

Claude Desktop から GA-shift MCPサーバーを利用するには、`claude_desktop_config.json` に以下を追加してください。

**設定ファイルの場所:**

| OS | パス |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

**設定コード（木町家環境）:**

```json
{
  "mcpServers": {
    "ga-shift": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--directory", "/Users/k-kawahara/Nest/kimachiya-shift",
        "python", "-m", "ga_shift.mcp"
      ]
    }
  }
}
```

**汎用テンプレート（環境に合わせて変更）:**

```json
{
  "mcpServers": {
    "ga-shift": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/kimachiya-shift",
        "python", "-m", "ga_shift.mcp"
      ]
    }
  }
}
```

> **ポイント**: `--directory` を使うことで `cwd` に依存せず、どこからでもMCPサーバーを起動できます。`uv` のフルパスを指定すると、Claude Desktopのシェル環境に依存しません。

**設定後の確認:**

1. Claude Desktop を再起動
2. チャット画面で MCP ツールアイコン（🔧）をクリック
3. `ga-shift` サーバーの15ツールが表示されることを確認
4. 「木町家のシフトを作りたい」と入力して動作確認

## 使い方

### 1. チャット式AI UI（推奨）

```bash
uv run streamlit run src/ga_shift/ui/chat_app.py
```

自然言語で対話しながらシフトを作成できます。

```
ユーザー: 木町家のシフトを作りたい
AI:       事業所の情報を教えてください。スタッフは何名ですか？
ユーザー: 5名です。川崎、斎藤、平田、島村、橋本で、島村さんは毎週水曜通院です
AI:       設定を登録しました。来月のテンプレートを生成しますか？
ユーザー: はい、3月分をお願いします
AI:       テンプレートを生成しました。希望休を入力したらアップロードしてください。
...
```

サイドバーからExcelのアップロード・ダウンロードも可能です。

### 2. タブ式Web UI

```bash
uv run streamlit run src/ga_shift/ui/app.py
```

| タブ | 説明 |
|------|------|
| **入力データ** | Excelファイルをアップロードし、社員情報や希望休をプレビュー |
| **制約設定** | 14種のテンプレートからON/OFFとパラメータを調整 |
| **GA実行** | 世代数・エリート数などを設定し、進捗バー付きでGA実行 |
| **結果** | シフト表・違反一覧を確認し、結果Excelをダウンロード |

### 3. MCPサーバー（Claude Desktop / AI連携）

```bash
# MCPサーバー単体起動（stdio モード）
uv run python -m ga_shift.mcp
```

設定方法は上記「Claude Desktop 設定」セクションを参照してください。

### 4. Jupyter Notebook で利用する

Jupyter Lab を使って、テンプレート生成から最適化実行までをノートブック上で操作できます。

```bash
# Jupyter Lab 起動
cd ~/Nest/kimachiya-shift
uv run jupyter lab
```

ブラウザで `notebooks/kimachiya_shift.ipynb` を開き、以下の流れで操作します:

| ステップ | 操作 | 説明 |
|:---:|:---|:---|
| 0 | `YEAR` と `MONTH` を設定 | 対象年月をセルで指定 |
| 1 | テンプレート生成セルを実行 | `output/shift_template_YYYY_MM.xlsx` が作成される |
| — | **Excelで◎を入力して保存** | 希望休を入力する唯一の手作業 |
| 2 | 最適化実行セルを実行 | GA実行 → `output/shift_result_YYYY_MM.xlsx` が出力される |
| 3 | 結果サマリーセルを実行 | シフト表と制約違反をノートブック上で確認 |

結果Excelには「GA結果シフト表」（色分け済み）と「バリデーション結果」の2シートが含まれます。

### 5. Python API

```python
from ga_shift.agents.conductor import ConductorAgent
from ga_shift.io.excel_reader import read_shift_input
from ga_shift.models.ga_config import GAConfig

shift_input = read_shift_input("shift_input.xlsx")
conductor = ConductorAgent()
result = conductor.run_full_pipeline(
    shift_input=shift_input,
    ga_config=GAConfig(generation_count=50),
    output_path="shift_result.xlsx",
)
print(f"最終スコア: {result['shift_result'].best_score}")
```

## Agno Agent 一覧（9 Agents）

| Phase | Agent | ID | 役割 |
|-------|-------|----|------|
| Core | ヒアリングAgent | `hearing-agent` | 事業所情報の収集・設定 |
| Core | 最適化Agent | `optimizer-agent` | テンプレート生成・GA最適化実行 |
| Core | 調整Agent | `adjuster-agent` | 結果説明・手動調整 |
| B | Neo4jブリッジAgent | `neo4j-bridge-agent` | support-db通院情報→シフト制約変換 |
| C | モニタリングAgent | `monitoring-agent` | シフト公平性・偏り分析 |
| C | コンプライアンスAgent | `compliance-agent` | 人員配置基準チェック |
| C | 引き継ぎAgent | `handover-agent` | 人事異動・入退社対応 |
| D | レポートAgent | `report-agent` | 月次総合レポート（品質スコア付き） |
| D | シミュレーションAgent | `simulation-agent` | What-ifシナリオ影響分析 |

Team構成は `create_shift_team()` のパラメータで柔軟に変更できます:

```python
from ga_shift.agno_agents.team import create_shift_team

# 最小構成（3 Agent）
team = create_shift_team()

# フル構成（9 Agent）
team = create_shift_team(
    enable_neo4j=True,      # +1: Neo4jブリッジ
    enable_ops=True,        # +3: モニタリング・コンプライアンス・引き継ぎ
    enable_extended=True,   # +2: レポート・シミュレーション
)
```

## MCPツール一覧（15 Tools）

| # | ツール | Phase | 説明 |
|---|--------|-------|------|
| 1 | `setup_facility` | Core | 事業所の初期設定（名前、種別、スタッフ構成） |
| 2 | `add_constraint` | Core | 制約テンプレートの追加・カスタマイズ |
| 3 | `list_constraints` | Core | 利用可能な全制約テンプレートの一覧 |
| 4 | `generate_shift_template` | Core | 月次Excelテンプレートの生成 |
| 5 | `run_optimization` | Core | GAによるシフト最適化の実行 |
| 6 | `explain_result` | Core | 最適化結果のわかりやすい説明 |
| 7 | `adjust_schedule` | Core | 手動でのシフト調整（コンプライアンスチェック付き） |
| 8 | `check_compliance` | Core | 人員配置基準の充足状況チェック |
| 9 | `import_accompanied_visits` | B | 通院同行情報の取り込み（Neo4j連携） |
| 10 | `get_accompanied_visits` | B | 通院同行一覧の取得 |
| 11 | `analyze_schedule_balance` | C | シフト公平性分析（勤務日数・週末・連勤） |
| 12 | `get_staffing_requirements` | C | 人員配置基準の取得（施設種別対応） |
| 13 | `transfer_staff` | C | スタッフ異動処理（追加・削除・更新） |
| 14 | `generate_shift_report` | D | 総合レポート生成（100点スコア + A〜Dグレード） |
| 15 | `simulate_scenario` | D | What-ifシミュレーション（退職/増員/利用者増/制約変更） |

## Excelテンプレート

入力Excelは以下のレイアウトです（シート名: `シフト表`）:

```
       A         B       C         D      E  F  ...
Row 0: シフト表（2026年3月）                      ← タイトル
Row 1: (空行)
Row 2: 社員名  雇用形態  セクション  有休残  1  2  ...
Row 3: 曜日                               日  月  ...
Row 4: 川崎聡  正規    仕込み・ランチ   3        ◎ ...
 ...
```

| セル | コード | 意味 |
|------|--------|------|
| 空欄 | 0 | 出勤可能（GAがスケジューリング） |
| `休` | 1 | GAが割り当てた休日 |
| `◎` | 2 | 希望休（固定、GAは変更しない） |
| `×` | 3 | 出勤不可日（固定） |

## 制約テンプレート一覧

### パターン制約
| 制約 | 説明 | 主要パラメータ |
|------|------|---------------|
| 長期連続勤務抑制 | N日以上の連勤にペナルティ | 閾値日数, 重み |
| 飛び石連休抑制 | 休-出-休パターンにペナルティ | 重み |
| 孤立出勤日抑制 | 休-出-休パターンにペナルティ | 重み |
| 連続休日ボーナス | 連休にボーナス（負のペナルティ） | 最小日数, 1日あたりボーナス |

### 日別制約
| 制約 | 説明 | 主要パラメータ |
|------|------|---------------|
| 必要出勤人数の充足 | 出勤人数と必要人数の差にペナルティ | 人数差あたりペナルティ |
| 特定日の最低出勤人数 | 指定日に最低人数を確保 | 対象日, 最低人数 |
| 特定日の最大出勤人数 | 指定日に上限を設定 | 対象日, 最大人数 |
| スキル別最低出勤人数 | 特定スキル保持者の出勤を確保 | スキル名, 最低人数 |

### 社員制約
| 制約 | 説明 | 主要パラメータ |
|------|------|---------------|
| 連続勤務上限 | 連勤日数のハード上限 | 上限日数 |
| 週末休日確保 | 月内で最低限の土日休日を確保 | 最低週末休日数 |
| 週当たり最低休日 | 7日間ウィンドウで休日を確保 | 週最低休日数 |
| 連勤後の休日確保 | N連勤後に休日がない場合にペナルティ | 閾値日数 |

### 公平性制約
| 制約 | 説明 | 主要パラメータ |
|------|------|---------------|
| 週末休日の公平配分 | 社員間の週末休日数差を抑制 | 許容差 |
| 休日の曜日偏り抑制 | 休日が特定曜日に偏ることを抑制 | 重み |

### 木町家専用制約
| 制約 | ペナルティ | 説明 |
|------|-----------|------|
| キッチン最低人員 | 50 | 仕込み・ランチセクションの最低出勤人数を確保 |
| 代役ルール | 40 | 島村休→斎藤が出勤する代替ルール |
| 有給取得上限 | 20 | 有休残日数以上の希望休を抑制 |
| 出勤不可日保護 | 1000 | ×マークの日に出勤を割り当てない（ハード制約） |
| 定休日制約（土日） | 500 / 100 | 土日は定休日（ハード制約500）。研修等の臨時営業日は正規のみ出勤可、パートは100のソフトペナルティ |

## プロジェクト構成

```
kimachiya-shift/
├── README.md                     ← このファイル
├── HANDOVER.md                   ← プロジェクト引き継ぎ資料
├── GA-SHIFT-AGNO-PLAN.md        ← Agno再構成設計書
├── SETUP_GUIDE.md                ← セットアップ手順
├── pyproject.toml                ← プロジェクト設定・依存関係
│
├── docs/
│   └── architecture-wireframe.html ← アーキテクチャ ワイヤーフレーム
│
├── src/ga_shift/
│   ├── models/                   ← Pydanticデータモデル
│   │   ├── schedule.py           ← ShiftInput, ShiftResult
│   │   ├── employee.py           ← EmployeeInfo
│   │   ├── constraint.py         ← ConstraintConfig, ConstraintSet
│   │   ├── ga_config.py          ← GAConfig
│   │   └── validation.py         ← ValidationReport
│   │
│   ├── ga/                       ← GAエンジン
│   │   ├── engine.py             ← メインGA実行
│   │   ├── operators.py          ← 交叉・突然変異
│   │   ├── population.py         ← 初期集団生成
│   │   └── evaluation.py         ← 適応度評価
│   │
│   ├── constraints/              ← 制約テンプレートシステム（14種+5木町家専用=19制約）
│   │   ├── registry.py           ← ConstraintRegistry（プラグイン管理）
│   │   ├── kimachi_constraints.py← 木町家専用制約
│   │   ├── pattern_constraints.py
│   │   ├── day_constraints.py
│   │   ├── employee_constraints.py
│   │   └── fairness_constraints.py
│   │
│   ├── io/                       ← Excel入出力
│   │   ├── excel_reader.py       ← read_shift_input()
│   │   ├── excel_writer.py       ← 結果出力
│   │   └── template_generator.py ← テンプレート生成
│   │
│   ├── agents/                   ← 内部エージェント（5体構成）
│   │   ├── conductor.py          ← パイプライン統括
│   │   ├── constraint_builder.py
│   │   ├── ga_engine.py
│   │   ├── validator.py
│   │   └── reporter.py
│   │
│   ├── mcp/                      ← MCP サーバー
│   │   ├── server.py             ← FastMCPサーバー（15ツール）
│   │   └── __main__.py           ← python -m ga_shift.mcp
│   │
│   ├── agno_agents/              ← Agno AIエージェント（9 Agent）
│   │   ├── team.py               ← ShiftTeam（統括・ルーティング）
│   │   ├── hearing.py            ← ヒアリングAgent [Core]
│   │   ├── optimizer.py          ← 最適化Agent [Core]
│   │   ├── adjuster.py           ← 調整Agent [Core]
│   │   ├── neo4j_bridge.py       ← Neo4jブリッジAgent [B]
│   │   ├── monitoring.py         ← モニタリングAgent [C]
│   │   ├── compliance.py         ← コンプライアンスAgent [C]
│   │   ├── handover.py           ← 引き継ぎAgent [C]
│   │   ├── report.py             ← レポートAgent [D]
│   │   └── simulation.py         ← シミュレーションAgent [D]
│   │
│   └── ui/                       ← Streamlit Web UI
│       ├── app.py                ← タブ式UI
│       ├── chat_app.py           ← チャット式AI UI
│       ├── components/           ← UIコンポーネント
│       └── pages/                ← 各タブページ
│
├── notebooks/
│   └── kimachiya_shift.ipynb     ← Jupyter Notebook（テンプレート生成→最適化→結果確認）
│
├── scripts/
│   └── chat_constraints.py       ← チャット形式の制約設定
│
└── tests/                        ← テストスイート（270件）
    ├── test_agents/              ← 内部エージェントテスト
    ├── test_constraints/         ← 制約テスト
    ├── test_ga/                  ← GAエンジンテスト
    ├── test_io/                  ← Excel I/Oテスト
    ├── test_mcp/                 ← MCPツール・クライアントテスト
    │   ├── test_tools.py         ← 15ツール単体テスト
    │   └── test_mcp_client.py    ← MCP結合テスト
    └── test_agno/                ← Agnoエージェントテスト
        ├── test_agents.py        ← コアAgent [Core]
        ├── test_neo4j_bridge.py  ← Neo4jブリッジ [B]
        ├── test_ops_agents.py    ← 運用Agent [C]
        ├── test_extended_agents.py ← 拡張Agent [D]
        └── test_chat_app.py      ← Chat UI統合
```

## 開発

```bash
# テスト実行（270件）
uv run pytest tests/ -q

# 詳細テスト（テスト名表示）
uv run pytest tests/ -v

# リント
uv run ruff check src/ tests/

# 型チェック
uv run mypy src/ga_shift/
```

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| GAエンジン | NumPy（スケジュール行列演算）、独自GA実装 |
| データモデル | Pydantic v2 |
| Excel I/O | openpyxl, pandas |
| MCPサーバー | FastMCP |
| AIエージェント | Agno（Claude claude-sonnet-4-5-20250929） |
| メモリ永続化 | Agno Memory + SQLite（SqliteDb） |
| グラフDB連携 | Neo4j（support-db MCP） |
| Web UI | Streamlit |
| テスト | pytest, pytest-asyncio |
| ノートブック | Jupyter Lab, ipykernel |
| パッケージ管理 | uv + hatchling |

## 謝辞

本プロジェクトの遺伝的アルゴリズム（GA）によるシフト表自動作成のアプローチは、**こいこいの人工知能研究室**（[こいこい](https://www.youtube.com/@koikoiai)）さんの研究・解説をベースにしています。GAの基本設計（個体表現・一様交叉・突然変異・エリート保存・制約ベース評価）は、こいこいさんのアイデアをほぼそのまま採用させていただきました。

## ライセンス

MIT
