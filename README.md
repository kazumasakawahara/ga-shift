# GA-Shift: シフト表自動作成システム

遺伝的アルゴリズム（GA）と5エージェント構成による、シフト表自動作成Webアプリケーションです。

## 特徴

- **14種類の制約テンプレート** — 連勤上限、飛び石連休抑制、公平性確保など、現場のニーズに合わせた制約をGUIで自由にカスタマイズ
- **Streamlit Web UI** — ブラウザから操作。Excelアップロード → 制約設定 → GA実行 → 結果ダウンロードまで一貫して完結
- **チャット形式の制約設定** — ターミナルで対話形式のスクリプトから制約を設定してGA実行も可能
- **Excel入出力** — 既存の勤務表Excelをそのまま入力し、結果もExcelで出力

## クイックスタート

```bash
# 1. リポジトリ取得
git clone <repository-url>
cd GA-shift

# 2. Python 仮想環境の作成とインストール（uvを使用）
uv venv --python 3.12
uv pip install -e ".[dev]"

# 3. テンプレートExcelの生成（2026年3月の例）
.venv/bin/python -m ga_shift.io.template_generator --year 2026 --month 3

# 4. Web UIを起動
.venv/bin/streamlit run src/ga_shift/ui/app.py
```

ブラウザで `http://localhost:8501` を開いてください。

> 詳しいセットアップ手順は [SETUP_GUIDE.md](SETUP_GUIDE.md) を参照してください。

## 使い方

### Web UI（推奨）

```bash
.venv/bin/streamlit run src/ga_shift/ui/app.py
```

4つのタブで操作します:

| タブ | 説明 |
|------|------|
| **入力データ** | Excelファイルをアップロードし、社員情報や希望休をプレビュー |
| **制約設定** | 14種のテンプレートからON/OFFとパラメータを調整 |
| **GA実行** | 世代数・エリート数などを設定し、進捗バー付きでGA実行 |
| **結果** | シフト表・違反一覧を確認し、結果Excelをダウンロード |

### チャット形式スクリプト（ターミナル操作）

```bash
.venv/bin/python scripts/chat_constraints.py
```

対話形式で制約を選び、パラメータを入力し、GAを実行できます。Excelファイルのパスを指定するだけで使えます。

### Python API

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

## Excelテンプレート

入力Excelは以下のレイアウトです（シート名: `シフト表`）:

```
       A         B   C   D   ...  AF   AG
Row 0: シフト表（2026年3月）             ← タイトル
Row 1: (空行)
Row 2: 社員名     1   2   3  ...  31   休日数
Row 3: 曜日       日  月  火  ...  火
Row 4: 社員A      ◎          ...        9
 ...   (社員データ 10名)
Row14: (空行)
Row15: 必要人数    7   7   7  ...  7
```

| セル | 意味 |
|------|------|
| 空欄 | 出勤可能（GAがスケジューリング） |
| `◎` | 希望休（固定、GAは変更しない） |
| 休日数 | 契約休日数（◎を含む合計） |
| 必要人数 | その日に必要な出勤人数 |

テンプレート生成コマンド:

```bash
.venv/bin/python -m ga_shift.io.template_generator --year 2026 --month 3 --employees 10
```

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

## プロジェクト構成

```
GA-shift/
├── README.md                  ← このファイル
├── SETUP_GUIDE.md             ← セットアップ手順
├── pyproject.toml             ← プロジェクト設定・依存関係
├── shift_input.xlsx           ← サンプル入力データ
├── scripts/
│   └── chat_constraints.py    ← チャット形式の制約設定スクリプト
├── src/ga_shift/
│   ├── models/                ← Pydanticデータモデル
│   ├── agents/                ← 5エージェント（Conductor, ConstraintBuilder, GAEngine, Validator, Reporter）
│   ├── constraints/           ← 制約テンプレートシステム（14種）
│   ├── ga/                    ← GAエンジン（operators, population, evaluation, engine）
│   ├── io/                    ← Excel入出力 + テンプレート生成
│   └── ui/                    ← Streamlit Web UI
└── tests/                     ← テストスイート
```

## 開発

```bash
# テスト実行
.venv/bin/python -m pytest tests/ -v

# リント
.venv/bin/ruff check src/ tests/

# 型チェック
.venv/bin/mypy src/ga_shift/
```

## 技術スタック

- Python 3.12
- numpy — スケジュール行列演算
- pandas / openpyxl — Excel入出力
- Pydantic v2 — データモデル・バリデーション
- Streamlit — Web UI
- 遺伝的アルゴリズム — 一様交叉 + 突然変異 + エリート保存

## ライセンス

MIT
