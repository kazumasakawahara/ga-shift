#!/usr/bin/env python3
"""
GA-Shift チャット形式 制約設定 & GA実行スクリプト

対話形式で制約を選択・パラメータ設定し、GAによるシフト表最適化を実行します。

使い方:
    .venv/bin/python scripts/chat_constraints.py
    .venv/bin/python scripts/chat_constraints.py --input shift_input.xlsx
    .venv/bin/python scripts/chat_constraints.py --input shift_input.xlsx --output result.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ga_shift.agents.conductor import ConductorAgent
from ga_shift.constraints.registry import get_registry
from ga_shift.io.excel_reader import read_shift_input
from ga_shift.io.template_generator import generate_template
from ga_shift.models.constraint import ConstraintConfig, ConstraintSet
from ga_shift.models.ga_config import GAConfig
from ga_shift.models.schedule import ShiftInput

# ─── 表示ユーティリティ ─────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"

_CATEGORY_LABELS = {
    "pattern": "パターン制約",
    "day": "日別制約",
    "employee": "社員制約",
    "fairness": "公平性制約",
}

_CATEGORY_ORDER = ["pattern", "day", "employee", "fairness"]


def _print_header(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─' * 50}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 50}{RESET}\n")


def _print_info(text: str) -> None:
    print(f"  {GREEN}✓{RESET} {text}")


def _print_warn(text: str) -> None:
    print(f"  {YELLOW}!{RESET} {text}")


def _print_error(text: str) -> None:
    print(f"  {RED}✗{RESET} {text}")


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"  {BOLD}?{RESET} {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return answer if answer else default


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    answer = _ask(f"{prompt} ({hint})", "y" if default else "n")
    return answer.lower() in ("y", "yes", "はい")


def _ask_int(prompt: str, default: int, min_val: int | None = None, max_val: int | None = None) -> int:
    while True:
        answer = _ask(prompt, str(default))
        try:
            val = int(answer)
            if min_val is not None and val < min_val:
                _print_warn(f"{min_val} 以上の値を入力してください")
                continue
            if max_val is not None and val > max_val:
                _print_warn(f"{max_val} 以下の値を入力してください")
                continue
            return val
        except ValueError:
            _print_warn("整数を入力してください")


def _ask_float(prompt: str, default: float, min_val: float | None = None, max_val: float | None = None) -> float:
    while True:
        answer = _ask(prompt, str(default))
        try:
            val = float(answer)
            if min_val is not None and val < min_val:
                _print_warn(f"{min_val} 以上の値を入力してください")
                continue
            if max_val is not None and val > max_val:
                _print_warn(f"{max_val} 以下の値を入力してください")
                continue
            return val
        except ValueError:
            _print_warn("数値を入力してください")


def _ask_choice(prompt: str, options: list[str]) -> int:
    """選択肢を表示して番号を返す（0-indexed）。"""
    print(f"\n  {BOLD}?{RESET} {prompt}")
    for i, opt in enumerate(options):
        print(f"    {DIM}[{i + 1}]{RESET} {opt}")
    while True:
        answer = _ask("番号を入力")
        try:
            idx = int(answer) - 1
            if 0 <= idx < len(options):
                return idx
            _print_warn(f"1〜{len(options)} の番号を入力してください")
        except ValueError:
            _print_warn("番号を入力してください")


# ─── メイン処理 ─────────────────────────────────────


def step_load_excel() -> ShiftInput:
    """ステップ1: Excelファイルの読み込み。"""
    _print_header("ステップ 1/4: 入力データの読み込み")

    while True:
        filepath = _ask("Excelファイルのパスを入力", "shift_input.xlsx")

        if not Path(filepath).exists():
            _print_error(f"ファイルが見つかりません: {filepath}")

            if _ask_yes_no("テンプレートを新規生成しますか?", default=False):
                year = _ask_int("年を入力", 2026, 2020, 2100)
                month = _ask_int("月を入力 (1-12)", 1, 1, 12)
                employees = _ask_int("社員数", 10, 1, 50)
                out_name = f"shift_input_{year}_{month:02d}.xlsx"
                generate_template(out_name, year, month, num_employees=employees)
                _print_info(f"テンプレートを生成しました: {out_name}")
                _print_warn("Excelを編集してから再度実行してください。")
                sys.exit(0)
            continue

        try:
            si = read_shift_input(filepath)
            _print_info(f"{si.num_employees}名 x {si.num_days}日 のデータを読み込みました")

            # 社員一覧を表示
            print()
            print(f"  {DIM}社員一覧:{RESET}")
            for emp in si.employees:
                pref = ", ".join(str(d) for d in emp.preferred_days_off) or "なし"
                print(f"    {emp.name}  休日数={emp.required_holidays}  希望休=[{pref}]")
            print()
            return si

        except Exception as e:
            _print_error(f"読み込みエラー: {e}")
            _print_warn("正しいフォーマットのExcelファイルを指定してください")


def step_select_constraints() -> ConstraintSet:
    """ステップ2: 制約の選択とパラメータ設定。"""
    _print_header("ステップ 2/4: 制約の設定")

    registry = get_registry()

    # プリセット選択
    preset_choice = _ask_choice(
        "制約セットの選び方を選んでください",
        [
            f"{GREEN}デフォルト（3制約 — まずはこれで試す）{RESET}",
            f"{CYAN}対話形式で1つずつ選ぶ{RESET}",
            f"全制約ON（14制約すべて有効）",
            f"制約なし（ペナルティなしでGA実行）",
        ],
    )

    if preset_choice == 0:
        cs = ConstraintSet.default_set()
        _print_info("デフォルト制約セットを選択しました")
        _show_constraint_summary(cs)

        if _ask_yes_no("パラメータを調整しますか?", default=False):
            cs = _tune_parameters(cs)
        return cs

    elif preset_choice == 1:
        return _interactive_select(registry)

    elif preset_choice == 2:
        configs = [ConstraintConfig(template_id=t.template_id, enabled=True) for t in registry.list_all()]
        cs = ConstraintSet(name="all", constraints=configs)
        _print_info("全14制約を有効にしました")
        _show_constraint_summary(cs)

        if _ask_yes_no("パラメータを調整しますか?", default=False):
            cs = _tune_parameters(cs)
        return cs

    else:
        _print_warn("制約なしで実行します")
        return ConstraintSet(name="none", constraints=[])


def _interactive_select(registry) -> ConstraintSet:
    """対話形式で制約を1つずつ選択。"""
    configs: list[ConstraintConfig] = []

    for category in _CATEGORY_ORDER:
        templates = registry.list_by_category(category)
        if not templates:
            continue

        label = _CATEGORY_LABELS.get(category, category)
        print(f"\n  {BOLD}── {label} ──{RESET}")

        for template in templates:
            desc = f"{template.name_ja}: {template.description}"
            print(f"\n    {CYAN}{template.name_ja}{RESET}")
            print(f"    {DIM}{template.description}{RESET}")

            if _ask_yes_no(f"  「{template.name_ja}」を有効にしますか?", default=False):
                params = _ask_parameters(template)
                configs.append(ConstraintConfig(
                    template_id=template.template_id,
                    enabled=True,
                    parameters=params,
                ))
                _print_info(f"追加しました: {template.name_ja}")

    cs = ConstraintSet(name="custom", constraints=configs)
    _show_constraint_summary(cs)
    return cs


def _ask_parameters(template) -> dict:
    """制約のパラメータを対話形式で入力。"""
    params = {}
    if not template.parameters:
        return params

    print(f"    {DIM}パラメータ設定 (Enterでデフォルト値を使用):{RESET}")
    for pdef in template.parameters:
        if pdef.param_type.value == "int":
            val = _ask_int(
                f"    {pdef.display_name}",
                int(pdef.default),
                int(pdef.min_value) if pdef.min_value is not None else None,
                int(pdef.max_value) if pdef.max_value is not None else None,
            )
            params[pdef.name] = val
        elif pdef.param_type.value == "float":
            val = _ask_float(
                f"    {pdef.display_name}",
                float(pdef.default),
                float(pdef.min_value) if pdef.min_value is not None else None,
                float(pdef.max_value) if pdef.max_value is not None else None,
            )
            params[pdef.name] = val
        elif pdef.param_type.value == "select":
            val = _ask(f"    {pdef.display_name}", str(pdef.default))
            params[pdef.name] = val
        elif pdef.param_type.value == "bool":
            val = _ask_yes_no(f"    {pdef.display_name}", bool(pdef.default))
            params[pdef.name] = val

    return params


def _tune_parameters(cs: ConstraintSet) -> ConstraintSet:
    """既存の制約セットのパラメータを調整。"""
    registry = get_registry()
    new_configs: list[ConstraintConfig] = []

    for config in cs.constraints:
        template = registry.get(config.template_id)
        print(f"\n  {CYAN}{template.name_ja}{RESET} のパラメータ:")
        params = {}

        for pdef in template.parameters:
            current = config.parameters.get(pdef.name, pdef.default)
            if pdef.param_type.value == "int":
                params[pdef.name] = _ask_int(
                    f"    {pdef.display_name}",
                    int(current),
                    int(pdef.min_value) if pdef.min_value is not None else None,
                    int(pdef.max_value) if pdef.max_value is not None else None,
                )
            elif pdef.param_type.value == "float":
                params[pdef.name] = _ask_float(
                    f"    {pdef.display_name}",
                    float(current),
                    float(pdef.min_value) if pdef.min_value is not None else None,
                    float(pdef.max_value) if pdef.max_value is not None else None,
                )
            else:
                params[pdef.name] = _ask(f"    {pdef.display_name}", str(current))

        new_configs.append(ConstraintConfig(
            template_id=config.template_id,
            enabled=True,
            parameters=params,
        ))

    return ConstraintSet(name=cs.name, constraints=new_configs)


def _show_constraint_summary(cs: ConstraintSet) -> None:
    """制約セットのサマリーを表示。"""
    registry = get_registry()
    enabled = [c for c in cs.constraints if c.enabled]
    print(f"\n  {BOLD}有効な制約 ({len(enabled)}個):{RESET}")
    for c in enabled:
        template = registry.get(c.template_id)
        param_str = ", ".join(f"{k}={v}" for k, v in c.parameters.items()) if c.parameters else "デフォルト"
        print(f"    {GREEN}●{RESET} {template.name_ja}  {DIM}({param_str}){RESET}")
    print()


def step_configure_ga() -> GAConfig:
    """ステップ3: GA設定。"""
    _print_header("ステップ 3/4: GA設定")

    if _ask_yes_no("デフォルト設定で実行しますか? (世代数=50, エリート数=20)", default=True):
        config = GAConfig()
        _print_info(f"デフォルト設定: 世代数={config.generation_count}, エリート数={config.elite_count}")
        return config

    generation_count = _ask_int("世代数", 50, 1, 500)
    elite_count = _ask_int("エリート数", 20, 2, 100)
    initial_population = _ask_int("初期個体数", 100, 10, 1000)
    crossover_rate = _ask_float("交叉率 (0.0〜1.0)", 0.5, 0.0, 1.0)
    mutation_rate = _ask_float("突然変異率 (0.0〜0.5)", 0.05, 0.0, 0.5)

    config = GAConfig(
        generation_count=generation_count,
        elite_count=elite_count,
        initial_population=initial_population,
        crossover_rate=crossover_rate,
        mutation_rate=mutation_rate,
    )
    _print_info(f"GA設定: 世代数={generation_count}, エリート数={elite_count}, 個体数={initial_population}")
    return config


def step_run_ga(
    shift_input: ShiftInput,
    constraint_set: ConstraintSet,
    ga_config: GAConfig,
    output_path: str,
) -> None:
    """ステップ4: GA実行と結果表示。"""
    _print_header("ステップ 4/4: GA実行")

    print(f"  設定サマリー:")
    print(f"    入力: {shift_input.num_employees}名 x {shift_input.num_days}日")
    enabled = [c for c in constraint_set.constraints if c.enabled]
    print(f"    制約: {len(enabled)}個")
    print(f"    世代数: {ga_config.generation_count}")
    print(f"    出力先: {output_path}")
    print()

    if not _ask_yes_no("実行しますか?", default=True):
        print("  キャンセルしました。")
        sys.exit(0)

    print()

    def progress(gen: int, score: float, top: float) -> None:
        bar_len = 30
        filled = int(bar_len * gen / ga_config.generation_count)
        bar = "█" * filled + "░" * (bar_len - filled)
        pct = gen / ga_config.generation_count * 100
        print(f"\r  {bar} {pct:5.1f}%  世代{gen:3d}  スコア: {top:.0f}  ", end="", flush=True)

    conductor = ConductorAgent()
    result = conductor.run_full_pipeline(
        shift_input=shift_input,
        constraint_set=constraint_set,
        ga_config=ga_config,
        output_path=output_path,
        progress_callback=progress,
    )

    print()  # 改行

    sr = result["shift_result"]
    vr = result["validation_report"]

    _print_header("結果")

    print(f"  {BOLD}最終スコア: {sr.best_score:.0f}{RESET}")
    print(f"  合計ペナルティ: {vr.total_penalty:.1f}")
    print(f"  エラー数: {vr.error_count}")
    print(f"  警告数: {vr.warning_count}")
    print()

    # 制約別スコア
    if vr.constraint_scores:
        print(f"  {BOLD}制約別スコア:{RESET}")
        for cs in vr.constraint_scores:
            icon = f"{GREEN}●{RESET}" if cs.penalty == 0 else (f"{RED}●{RESET}" if cs.penalty >= 10 else f"{YELLOW}●{RESET}")
            print(f"    {icon} {cs.constraint_name}: ペナルティ {cs.penalty:.1f}")
        print()

    # 違反詳細
    if vr.violations:
        print(f"  {BOLD}違反一覧:{RESET}")
        for v in vr.violations:
            icon = f"{RED}✗{RESET}" if v.severity.value == "error" else f"{YELLOW}!{RESET}"
            print(f"    {icon} [{v.constraint_id}] {v.message}")
        print()

    # 日別出勤人数サマリー
    import numpy as np
    schedule = sr.best_schedule
    binary = np.where(schedule == 2, 1, schedule)
    mismatch_days = []
    for d in range(shift_input.num_days):
        workers = shift_input.num_employees - int(np.sum(binary[:, d]))
        required = int(shift_input.required_workers[d])
        if workers != required:
            mismatch_days.append(f"{d+1}日({workers}/{required}人)")

    if mismatch_days:
        print(f"  {YELLOW}人数不一致の日: {', '.join(mismatch_days)}{RESET}")
    else:
        print(f"  {GREEN}全日で必要人数を充足しています{RESET}")

    print()
    _print_info(f"結果を保存しました: {output_path}")

    # 再実行の提案
    print()
    if _ask_yes_no("パラメータを変えて再実行しますか?", default=False):
        return "retry"

    print(f"\n  {DIM}お疲れさまでした!{RESET}\n")
    return None


# ─── エントリポイント ────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GA-Shift チャット形式 制約設定 & GA実行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", "-i", default=None, help="入力Excelファイルのパス")
    parser.add_argument("--output", "-o", default="shift_result.xlsx", help="出力Excelファイルのパス")
    args = parser.parse_args()

    print()
    print(f"  {BOLD}{CYAN}╔══════════════════════════════════════════╗{RESET}")
    print(f"  {BOLD}{CYAN}║   GA-Shift シフトスケジューラー          ║{RESET}")
    print(f"  {BOLD}{CYAN}║   チャット形式 制約設定 & GA実行         ║{RESET}")
    print(f"  {BOLD}{CYAN}╚══════════════════════════════════════════╝{RESET}")
    print(f"  {DIM}Ctrl+C でいつでも中断できます{RESET}")

    # コマンドライン引数があればスキップ
    if args.input and Path(args.input).exists():
        shift_input = read_shift_input(args.input)
        _print_info(f"{args.input} を読み込みました ({shift_input.num_employees}名 x {shift_input.num_days}日)")
    else:
        shift_input = step_load_excel()

    while True:
        constraint_set = step_select_constraints()
        ga_config = step_configure_ga()
        result = step_run_ga(shift_input, constraint_set, ga_config, args.output)
        if result != "retry":
            break


if __name__ == "__main__":
    main()
