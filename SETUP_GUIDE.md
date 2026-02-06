# GA-Shift セットアップガイド

このガイドでは、GA-Shift を初めて使う方がゼロからセットアップして動かすまでの手順を説明します。

---

## 動作環境

| 項目 | 要件 |
|------|------|
| OS | macOS / Linux / Windows (WSL推奨) |
| Python | 3.11 以上（3.12 推奨） |
| パッケージマネージャ | [uv](https://docs.astral.sh/uv/)（推奨）または pip |
| ブラウザ | Chrome / Firefox / Safari / Edge（Streamlit UI用） |

---

## 1. 前提ツールのインストール

### uv（推奨パッケージマネージャ）

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Homebrew
brew install uv

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

インストール確認:

```bash
uv --version
# uv 0.8.x のように表示されればOK
```

> **uv を使わない場合**: 後述の「pip を使う場合」を参照してください。

### Python 3.12

uv を使えば Python のインストールも自動で行われます。手動でインストールする場合:

```bash
# macOS (Homebrew)
brew install python@3.12

# Ubuntu / Debian
sudo apt update && sudo apt install python3.12 python3.12-venv

# Windows
# https://www.python.org/downloads/ からダウンロード
```

---

## 2. プロジェクトの取得

```bash
git clone <repository-url>
cd GA-shift
```

リポジトリがない場合は、プロジェクトフォルダを直接コピーして `cd GA-shift` してください。

---

## 3. 環境構築

### uv を使う場合（推奨）

```bash
# 仮想環境を作成（Python 3.12 が自動でダウンロードされます）
uv venv --python 3.12

# パッケージをインストール
uv pip install -e ".[dev]"
```

### pip を使う場合

```bash
# 仮想環境を作成
python3.12 -m venv .venv

# 有効化
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# パッケージをインストール
pip install -e ".[dev]"
```

### インストール確認

```bash
.venv/bin/python -c "import ga_shift; print('OK')"
# OK と表示されれば成功
```

---

## 4. 入力Excelの準備

### テンプレートを生成する

```bash
# 2026年3月のテンプレート（10名分）を生成
.venv/bin/python -m ga_shift.io.template_generator --year 2026 --month 3
```

生成されたファイル `shift_input_2026_03.xlsx` をExcelで開いて編集します。

### テンプレートの記入方法

1. **社員名** — A列のセルに社員名を入力
2. **希望休** — 休みたい日のセルに `◎` を入力
3. **休日数** — 右端の列に各社員の契約休日数を入力（◎を含む合計）
4. **必要人数** — 最下行で各日の必要出勤人数を調整

**記入例:**

| 社員名 | 1 | 2 | 3 | 4 | 5 | ... | 休日数 |
|--------|---|---|---|---|---|-----|--------|
| 田中 | | ◎ | | | | ... | 9 |
| 佐藤 | | | | ◎ | ◎ | ... | 10 |
| 必要人数 | 7 | 7 | 7 | 7 | 7 | ... | |

> サンプルファイル `shift_input.xlsx` が同梱されています。まずはこれを使って動作確認できます。

---

## 5. アプリケーションの起動

### 方法A: Web UI（推奨）

```bash
.venv/bin/streamlit run src/ga_shift/ui/app.py
```

ブラウザが自動で開きます（`http://localhost:8501`）。

**操作手順:**

1. 「入力データ」タブで Excel をアップロード
2. 「制約設定」タブで使いたい制約をON/OFFし、パラメータを調整
3. 「GA実行」タブで世代数などを設定し「GA実行」ボタンをクリック
4. 「結果」タブでシフト表を確認し、Excelをダウンロード

### 方法B: チャット形式スクリプト（ターミナル操作）

```bash
.venv/bin/python scripts/chat_constraints.py
```

対話形式で操作できます:

```
GA-Shift シフトスケジューラー へようこそ!
? Excelファイルのパスを入力: shift_input.xlsx
  10名 x 31日のデータを読み込みました

? 制約を選んでください:
  [1] 長期連続勤務抑制（5連勤以上にペナルティ）
  [2] 飛び石連休抑制
  ...
```

### 方法C: Pythonスクリプト

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

---

## 6. 動作確認（テスト実行）

```bash
.venv/bin/python -m pytest tests/ -v
```

30件のテストが全てパスすれば環境構築は正常です。

---

## 7. 制約の選び方ガイド

初めて使う場合は、まず**デフォルト制約セット**（3制約）で試すことをお勧めします。

### デフォルト制約セット

| 制約 | 役割 |
|------|------|
| 長期連続勤務抑制 | 5日以上の連続勤務を防止 |
| 飛び石連休抑制 | 休-出-休の非効率パターンを防止 |
| 必要出勤人数の充足 | 各日の人員数を確保 |

### よくある追加制約の組み合わせ

**基本セット（デフォルト + 労務管理）:**
```
+ 連続勤務上限（6日）
+ 週当たり最低休日（1日/週）
```

**公平重視セット:**
```
+ 週末休日の公平配分（許容差2日）
+ 休日の曜日偏り抑制
```

**快適重視セット:**
```
+ 連続休日ボーナス（2連休以上にボーナス）
+ 連勤後の休日確保
+ 週末休日確保（月2日以上）
```

---

## 8. GA設定のチューニング

| パラメータ | デフォルト | 説明 | 推奨調整 |
|-----------|-----------|------|---------|
| 世代数 | 50 | 最適化の繰り返し回数 | 結果が悪い場合は100〜200に増やす |
| エリート数 | 20 | 各世代で残す上位個体数 | 通常変更不要 |
| 初期個体数 | 100 | 最初に生成するランダム解の数 | 通常変更不要 |
| 交叉率 | 0.5 | 遺伝子が入れ替わる確率 | 通常変更不要 |
| 突然変異率 | 0.05 | 突然変異が起きる確率 | 多様性が欲しい場合 0.1 に |

> 世代数50で1分以内、100で2〜3分程度が目安です（10名x31日の場合）。

---

## トラブルシューティング

### `ModuleNotFoundError: No module named 'ga_shift'`

```bash
# パッケージがインストールされていません
uv pip install -e ".[dev]"
```

### `'ga_shift' is not a package`

プロジェクトルートに `ga_shift.py` というファイルがあるとパッケージと衝突します。`ga_shift_v1.py` にリネームしてください。

### Streamlitが起動しない

```bash
# Streamlitのバージョン確認
.venv/bin/streamlit --version

# ポートが使用中の場合
.venv/bin/streamlit run src/ga_shift/ui/app.py --server.port 8502
```

### テストが失敗する

```bash
# shift_input.xlsx がプロジェクトルートにあるか確認
ls shift_input.xlsx

# パッケージを再インストール
uv pip install -e ".[dev]" --force-reinstall
```

### Excel読み込みエラー

- シート名が「シフト表」であることを確認
- 行・列の挿入/削除をしていないか確認
- テンプレート生成コマンドで新しいファイルを作り直すのが確実です

---

## ファイル構成の概要

```
GA-shift/
├── README.md                  ← プロジェクト概要
├── SETUP_GUIDE.md             ← このファイル
├── pyproject.toml             ← 依存関係とビルド設定
├── shift_input.xlsx           ← サンプル入力データ
├── scripts/
│   └── chat_constraints.py    ← チャット形式の制約設定スクリプト
│
├── src/ga_shift/
│   ├── models/                ← データモデル（Pydantic）
│   │   ├── schedule.py        ←   ShiftInput, ShiftResult
│   │   ├── employee.py        ←   EmployeeInfo
│   │   ├── constraint.py      ←   ConstraintConfig, ConstraintSet
│   │   ├── ga_config.py       ←   GAConfig
│   │   └── validation.py      ←   ValidationReport
│   │
│   ├── constraints/           ← 制約テンプレート（14種）
│   │   ├── base.py            ←   ConstraintTemplate ABC
│   │   ├── registry.py        ←   全テンプレート管理
│   │   ├── pattern_constraints.py
│   │   ├── employee_constraints.py
│   │   ├── day_constraints.py
│   │   └── fairness_constraints.py
│   │
│   ├── agents/                ← 5エージェント
│   │   ├── conductor.py       ←   全体制御
│   │   ├── constraint_builder.py ← 制約コンパイル
│   │   ├── ga_engine.py       ←   GA実行
│   │   ├── validator.py       ←   結果検証
│   │   └── reporter.py        ←   Excel出力
│   │
│   ├── ga/                    ← GAエンジン
│   │   ├── engine.py          ←   メインループ
│   │   ├── operators.py       ←   交叉・突然変異
│   │   ├── population.py      ←   初期個体生成
│   │   └── evaluation.py      ←   制約ベース評価
│   │
│   ├── io/                    ← 入出力
│   │   ├── excel_reader.py    ←   Excel → ShiftInput
│   │   ├── excel_writer.py    ←   ShiftResult → Excel
│   │   └── template_generator.py ← テンプレート生成
│   │
│   └── ui/                    ← Streamlit Web UI
│       ├── app.py             ←   メインエントリ
│       ├── pages/             ←   4タブ（upload, constraints, execution, results）
│       └── components/        ←   共通部品
│
└── tests/                     ← テスト（30件）
```
