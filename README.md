# GA-Shift: シフト表自動作成システム

遺伝的アルゴリズム（GA）× AIエージェント（Agno）× MCP による、シフト表自動作成システムです。
福祉事業所（就労継続支援B型等）の月次スタッフシフトを、対話形式で自動生成します。

## 特徴

- **遺伝的アルゴリズム** — 一様交叉・突然変異・エリート保存による最適化で、制約を満たすシフト表を自動生成
- **14種類の制約テンプレート** — 連勤上限、公平性確保、キッチン最低人員など、プラグイン方式で自由にカスタマイズ
- **MCP（Model Context Protocol）サーバー** — GAエンジンを8つのツールとしてラップし、AIアシスタント（Claude Desktop等）から直接操作可能
- **Agno AIエージェントチーム** — ヒアリング → 最適化 → 調整 の3段階を対話的に支援
- **2種類のUI** — タブ式Web UI（従来型）とチャット式AI UI（Agno統合型）を選択可能
- **Excel入出力** — 既存の勤務表Excelをそのまま入力し、結果もExcelで出力

## アーキテクチャ

```
┌─────────────────────────────────────────────┐
│  Streamlit Chat UI  /  Claude Desktop       │  ← ユーザー接点
└──────────────┬──────────────────┬────────────┘
               │                 │
    ┌──────────▼──────────┐     │
    │  Agno ShiftTeam     │     │
    │  ├ HearingAgent     │     │
    │  ├ OptimizerAgent   │     │
    │  └ AdjusterAgent    │     │
    └──────────┬──────────┘     │
               │ MCPTools       │ MCP Protocol
    ┌──────────▼────────────────▼─────────────┐
    │  FastMCP Server (8 tools)               │  ← 境界層
    └──────────────────┬──────────────────────┘
                       │
    ┌──────────────────▼──────────────────────┐
    │  GA Core (変更なし)                      │
    │  ├ models/   — Pydantic データモデル     │
    │  ├ ga/       — GAエンジン               │
    │  ├ constraints/ — 制約レジストリ         │
    │  └ io/       — Excel入出力              │
    └─────────────────────────────────────────┘
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

# 3. テスト実行（52件）
uv run pytest tests/ -q

# 4. UI起動（いずれか）
uv run streamlit run src/ga_shift/ui/app.py       # タブ式UI
uv run streamlit run src/ga_shift/ui/chat_app.py   # チャット式AI UI
```

ブラウザで `http://localhost:8501` を開いてください。

> 詳しいセットアップ手順は [SETUP_GUIDE.md](SETUP_GUIDE.md) を参照してください。

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

Claude Desktop の `claude_desktop_config.json` に追加:

```json
{
  "mcpServers": {
    "ga-shift": {
      "command": "uv",
      "args": ["run", "python", "-m", "ga_shift.mcp"],
      "cwd": "/path/to/kimachiya-shift"
    }
  }
}
```

### 4. Python API

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

## MCPツール一覧

| ツール | 説明 |
|--------|------|
| `setup_facility` | 事業所の初期設定（名前、種別、スタッフ構成） |
| `add_constraint` | 制約テンプレートの追加・カスタマイズ |
| `list_constraints` | 利用可能な全制約テンプレートの一覧 |
| `generate_shift_template` | 月次Excelテンプレートの生成 |
| `run_optimization` | GAによるシフト最適化の実行 |
| `explain_result` | 最適化結果のわかりやすい説明 |
| `adjust_schedule` | 手動でのシフト調整（コンプライアンスチェック付き） |
| `check_compliance` | 人員配置基準の充足状況チェック |

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

## プロジェクト構成

```
kimachiya-shift/
├── README.md                     ← このファイル
├── HANDOVER.md                   ← プロジェクト引き継ぎ資料
├── GA-SHIFT-AGNO-PLAN.md        ← Agno再構成設計書
├── SETUP_GUIDE.md                ← セットアップ手順
├── pyproject.toml                ← プロジェクト設定・依存関係
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
│   ├── constraints/              ← 制約テンプレートシステム（14種+4木町家専用）
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
│   ├── mcp/                      ← MCP サーバー【NEW】
│   │   ├── server.py             ← FastMCPサーバー（8ツール）
│   │   └── __main__.py           ← python -m ga_shift.mcp
│   │
│   ├── agno_agents/              ← Agno AIエージェント【NEW】
│   │   ├── hearing.py            ← ヒアリングAgent
│   │   ├── optimizer.py          ← 最適化Agent
│   │   ├── adjuster.py           ← 調整Agent
│   │   └── team.py               ← ShiftTeam（統括）
│   │
│   └── ui/                       ← Streamlit Web UI
│       ├── app.py                ← タブ式UI
│       ├── chat_app.py           ← チャット式AI UI【NEW】
│       ├── components/           ← UIコンポーネント
│       └── pages/                ← 各タブページ
│
├── scripts/
│   └── chat_constraints.py       ← チャット形式の制約設定
│
└── tests/                        ← テストスイート（52件）
    ├── test_agents/
    ├── test_constraints/
    ├── test_ga/
    └── test_io/
```

## 開発

```bash
# テスト実行（52件）
uv run pytest tests/ -q

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
| Web UI | Streamlit |
| テスト | pytest |
| パッケージ管理 | uv + hatchling |

## ライセンス

MIT
