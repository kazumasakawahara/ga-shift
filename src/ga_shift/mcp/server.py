"""GA-shift MCP Server.

Exposes the GA-shift scheduling engine as MCP tools so that
AI agents (Claude, Agno, etc.) can interact with it via
the Model Context Protocol.

Usage:
    uv run python -m ga_shift.mcp.server        # stdio mode
    uv run fastmcp run ga_shift/mcp/server.py   # via CLI
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from fastmcp import FastMCP

from ga_shift.agents.conductor import ConductorAgent
from ga_shift.constraints.registry import get_registry
from ga_shift.io.excel_reader import read_shift_input
from ga_shift.io.template_generator import EmployeePreset, generate_template
from ga_shift.models.constraint import ConstraintConfig, ConstraintSet
from ga_shift.models.ga_config import GAConfig

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="ga-shift",
    instructions="""
    GA-shiftは遺伝的アルゴリズムによるシフト自動最適化システムです。
    福祉事業所（就労継続支援B型等）のスタッフシフトを自動生成します。

    基本フロー:
    1. setup_facility → 事業所の初期設定
    2. generate_template → Excelテンプレート生成
    3. (ユーザーが希望休を入力)
    4. run_optimization → GA実行
    5. explain_result → 結果の説明
    6. adjust_schedule → 手動調整（必要に応じて）
    7. check_compliance → 人員配置基準チェック
    """,
)

# ---------------------------------------------------------------------------
# In-memory facility state (per server session)
# ---------------------------------------------------------------------------
_facility_state: dict[str, Any] = {}


def _get_output_dir() -> Path:
    """Get or create the output directory for generated files."""
    out = Path(_facility_state.get("output_dir", tempfile.gettempdir())) / "ga_shift_output"
    out.mkdir(parents=True, exist_ok=True)
    return out


# ---------------------------------------------------------------------------
# Tool 1: setup_facility
# ---------------------------------------------------------------------------
@mcp.tool
def setup_facility(
    name: str,
    facility_type: str = "就労継続支援B型",
    sections: list[str] | None = None,
    staff: list[dict[str, Any]] | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """事業所の初期設定を行います。

    Args:
        name: 事業所名（例: "木町家"）
        facility_type: 事業種別（例: "就労継続支援B型"）
        sections: セクション一覧（例: ["仕込み", "ランチ"]）
        staff: スタッフ情報のリスト。各要素は以下の形式:
            {
                "name": "川崎聡",
                "employee_type": "正規",   # "正規" or "パート"
                "section": "仕込み",       # セクション名
                "vacation_days": 3,        # 有給残日数
                "holidays": 9,             # 月間休日数
                "unavailable_weekdays": [2] # 出勤不可の曜日 (0=月..6=日)
            }
        output_dir: 出力ディレクトリのパス

    Returns:
        設定結果のサマリー
    """
    _facility_state["name"] = name
    _facility_state["facility_type"] = facility_type
    _facility_state["sections"] = sections or []
    _facility_state["staff"] = staff or []
    if output_dir:
        _facility_state["output_dir"] = output_dir

    # Build employee presets
    presets = []
    for s in _facility_state["staff"]:
        presets.append(
            EmployeePreset(
                name=s["name"],
                employee_type=s.get("employee_type", "正規"),
                section=s.get("section", ""),
                vacation_days=s.get("vacation_days", 0),
                holidays=s.get("holidays", 9),
                unavailable_weekdays=s.get("unavailable_weekdays", []),
            )
        )
    _facility_state["employee_presets"] = presets

    return {
        "status": "ok",
        "facility_name": name,
        "facility_type": facility_type,
        "sections": _facility_state["sections"],
        "staff_count": len(presets),
        "staff_names": [p.name for p in presets],
    }


# ---------------------------------------------------------------------------
# Tool 2: add_constraint
# ---------------------------------------------------------------------------
@mcp.tool
def add_constraint(
    constraint_type: str,
    parameters: dict[str, Any] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """制約を追加します。

    Args:
        constraint_type: 制約テンプレートID。利用可能な制約:
            - "kitchen_min_workers": キッチン最低人員
            - "substitute_constraint": 代役ルール
            - "unavailable_day_hard": 出勤不可日の保護
            - "vacation_days_limit": 有給取得上限
            - "avoid_long_consecutive_work": 連続勤務の回避
            - "no_isolated_holidays": 孤立休日の回避
            - "no_isolated_workdays": 孤立出勤日の回避
            - "max_consecutive_work": 最大連続勤務日数
            - "min_days_off_per_week": 週最低休日数
            - "required_workers_match": 必要人員の充足
            - "equal_weekend_distribution": 土日休日の公平配分
        parameters: 制約固有のパラメータ（辞書）
        enabled: 有効/無効

    Returns:
        追加結果
    """
    registry = get_registry()

    # Verify template exists
    try:
        template = registry.get(constraint_type)
    except KeyError as e:
        available = [t.template_id for t in registry.list_all()]
        return {
            "status": "error",
            "message": str(e),
            "available_constraints": available,
        }

    config = ConstraintConfig(
        template_id=constraint_type,
        enabled=enabled,
        parameters=parameters or {},
    )

    # Store in facility state
    if "custom_constraints" not in _facility_state:
        _facility_state["custom_constraints"] = []
    _facility_state["custom_constraints"].append(config)

    return {
        "status": "ok",
        "constraint_type": constraint_type,
        "name_ja": template.name_ja,
        "parameters": parameters or {},
        "total_custom_constraints": len(_facility_state["custom_constraints"]),
    }


# ---------------------------------------------------------------------------
# Tool 3: list_constraints
# ---------------------------------------------------------------------------
@mcp.tool
def list_constraints() -> dict[str, Any]:
    """利用可能な全制約テンプレートの一覧を返します。

    Returns:
        制約テンプレートのリスト（ID、名称、カテゴリ、パラメータ定義）
    """
    registry = get_registry()
    templates = []
    for t in registry.list_all():
        templates.append(
            {
                "template_id": t.template_id,
                "name_ja": t.name_ja,
                "category": t.category,
                "parameters": [
                    {
                        "name": p.name,
                        "display_name": p.display_name,
                        "type": p.param_type.value,
                        "default": p.default,
                        "description": p.description,
                    }
                    for p in t.parameters
                ],
            }
        )
    return {"constraints": templates, "count": len(templates)}


# ---------------------------------------------------------------------------
# Tool 4: generate_template
# ---------------------------------------------------------------------------
@mcp.tool
def generate_shift_template(
    year: int,
    month: int,
    default_required: int = 5,
    kitchen_required: int | None = None,
    output_filename: str | None = None,
) -> dict[str, Any]:
    """Excelテンプレートファイルを生成します。

    事業所の設定情報（setup_facilityで設定済み）を使って、
    スタッフ情報が入ったシフト入力用Excelを生成します。

    Args:
        year: 対象年（例: 2026）
        month: 対象月（1-12）
        default_required: 1日あたりのデフォルト必要人数
        kitchen_required: キッチン最低人数（設定時のみ行追加）
        output_filename: 出力ファイル名（省略時は自動生成）

    Returns:
        生成されたファイルのパス情報
    """
    presets = _facility_state.get("employee_presets", [])
    facility_name = _facility_state.get("name", "shift")

    if not output_filename:
        output_filename = f"{facility_name}_{year}年{month}月_テンプレート.xlsx"

    output_path = _get_output_dir() / output_filename

    filepath = generate_template(
        filepath=output_path,
        year=year,
        month=month,
        num_employees=max(len(presets), 5),
        default_required=default_required,
        employee_presets=presets if presets else None,
        employee_names=[p.name for p in presets] if presets else None,
        kitchen_required=kitchen_required,
    )

    return {
        "status": "ok",
        "filepath": str(filepath),
        "year": year,
        "month": month,
        "staff_count": len(presets),
        "message": f"テンプレートを生成しました: {filepath.name}",
    }


# ---------------------------------------------------------------------------
# Tool 5: run_optimization
# ---------------------------------------------------------------------------
@mcp.tool
def run_optimization(
    input_path: str,
    output_path: str | None = None,
    constraint_preset: str = "auto",
    population_size: int = 100,
    generations: int = 50,
    mutation_rate: float = 0.05,
) -> dict[str, Any]:
    """遺伝的アルゴリズムでシフト最適化を実行します。

    Args:
        input_path: 希望休入力済みExcelファイルのパス
        output_path: 出力Excelファイルのパス（省略時は自動生成）
        constraint_preset: 制約プリセット名
            - "auto": カスタム制約があればそれを使用、なければ木町家デフォルト
            - "kimachiya": 木町家デフォルト
            - "default": 汎用デフォルト
        population_size: GA個体数
        generations: GA世代数
        mutation_rate: 突然変異率

    Returns:
        最適化結果のサマリー（スコア、違反数、出力パス等）
    """
    input_file = Path(input_path)
    if not input_file.exists():
        return {"status": "error", "message": f"ファイルが見つかりません: {input_path}"}

    # Read input
    shift_input = read_shift_input(input_file)

    # Build constraint set
    if constraint_preset == "auto" and "custom_constraints" in _facility_state:
        constraint_set = ConstraintSet(
            name="custom",
            constraints=_facility_state["custom_constraints"],
        )
    elif constraint_preset == "kimachiya":
        constraint_set = ConstraintSet.kimachi_default()
    else:
        constraint_set = ConstraintSet.default_set()

    # GA config
    ga_config = GAConfig(
        initial_population=population_size,
        generation_count=generations,
        mutation_rate=mutation_rate,
    )

    # Output path
    if not output_path:
        out_name = input_file.stem + "_最適化結果.xlsx"
        out_file = _get_output_dir() / out_name
    else:
        out_file = Path(output_path)

    # Run pipeline
    conductor = ConductorAgent()
    result = conductor.run_full_pipeline(
        shift_input=shift_input,
        constraint_set=constraint_set,
        ga_config=ga_config,
        output_path=out_file,
    )

    shift_result = result["shift_result"]
    validation = result["validation_report"]

    # Build human-readable summary
    schedule = shift_result.best_schedule
    work_days_per_staff = []
    for i, emp in enumerate(shift_input.employees):
        work_count = int(np.sum(schedule[i] == 0))
        work_days_per_staff.append({"name": emp.name, "work_days": work_count})

    return {
        "status": "ok",
        "best_score": round(shift_result.best_score, 2),
        "generations": shift_result.generation_count,
        "output_path": str(out_file),
        "is_compliant": validation.is_compliant,
        "error_count": validation.error_count,
        "warning_count": validation.warning_count,
        "work_days_per_staff": work_days_per_staff,
        "violations_summary": [
            {"constraint": v.constraint_id, "message": v.message, "severity": v.severity.value}
            for v in validation.violations[:10]  # Top 10 violations
        ],
    }


# ---------------------------------------------------------------------------
# Tool 6: explain_result
# ---------------------------------------------------------------------------
@mcp.tool
def explain_result(result_path: str) -> dict[str, Any]:
    """生成されたシフト結果をわかりやすく説明します。

    Excelの最適化結果ファイルを読み込み、各スタッフの勤務状況、
    制約充足状況などを構造化データとして返します。

    Args:
        result_path: 最適化結果Excelファイルのパス

    Returns:
        シフト内容のサマリー
    """
    result_file = Path(result_path)
    if not result_file.exists():
        return {"status": "error", "message": f"ファイルが見つかりません: {result_path}"}

    shift_input = read_shift_input(result_file)
    schedule = shift_input.base_schedule

    staff_summary = []
    for i, emp in enumerate(shift_input.employees):
        row = schedule[i]
        work_days = int(np.sum(row == 0))
        holidays = int(np.sum((row == 1) | (row == 2)))
        unavailable = int(np.sum(row == 3))

        # Find actual work/off day numbers
        work_day_nums = [d + 1 for d in range(len(row)) if row[d] == 0]
        off_day_nums = [d + 1 for d in range(len(row)) if row[d] in (1, 2)]

        staff_summary.append(
            {
                "name": emp.name,
                "employee_type": emp.employee_type.value,
                "section": emp.section.value if emp.section else "",
                "work_days": work_days,
                "holidays": holidays,
                "unavailable_days": unavailable,
                "off_day_numbers": off_day_nums,
            }
        )

    # Daily staffing
    daily_workers = []
    for d in range(shift_input.num_days):
        col = schedule[:, d]
        workers = [
            shift_input.employees[i].name for i in range(len(col)) if col[i] == 0
        ]
        daily_workers.append(
            {
                "day": d + 1,
                "label": shift_input.day_labels[d] if d < len(shift_input.day_labels) else "",
                "worker_count": len(workers),
                "workers": workers,
            }
        )

    return {
        "status": "ok",
        "staff_count": shift_input.num_employees,
        "total_days": shift_input.num_days,
        "staff_summary": staff_summary,
        "daily_staffing": daily_workers,
    }


# ---------------------------------------------------------------------------
# Tool 7: adjust_schedule
# ---------------------------------------------------------------------------
@mcp.tool
def adjust_schedule(
    result_path: str,
    changes: list[dict[str, Any]],
    output_path: str | None = None,
) -> dict[str, Any]:
    """シフト結果を手動で調整します。

    指定されたスタッフの指定日の出勤/休日を変更し、
    変更後の制約チェックを行います。

    Args:
        result_path: 最適化結果Excelファイルのパス
        changes: 変更リスト。各要素は以下の形式:
            {
                "staff_name": "川崎聡",
                "day": 15,           # 1-indexed
                "new_status": "off"  # "work" or "off"
            }
        output_path: 調整後の出力パス（省略時は上書き）

    Returns:
        調整結果と制約チェック結果
    """
    import openpyxl

    result_file = Path(result_path)
    if not result_file.exists():
        return {"status": "error", "message": f"ファイルが見つかりません: {result_path}"}

    shift_input = read_shift_input(result_file)

    # Apply changes to the schedule
    schedule = shift_input.base_schedule.copy()
    applied = []
    errors = []

    for change in changes:
        staff_name = change["staff_name"]
        day = change["day"]  # 1-indexed
        new_status = change["new_status"]

        # Find staff index
        staff_idx = None
        for i, emp in enumerate(shift_input.employees):
            if emp.name == staff_name:
                staff_idx = i
                break

        if staff_idx is None:
            errors.append(f"スタッフ '{staff_name}' が見つかりません")
            continue

        day_idx = day - 1  # Convert to 0-indexed
        if day_idx < 0 or day_idx >= shift_input.num_days:
            errors.append(f"日付 {day} は範囲外です (1-{shift_input.num_days})")
            continue

        current = schedule[staff_idx, day_idx]
        if current in (2, 3):  # Protected: preferred off or unavailable
            errors.append(
                f"{staff_name}の{day}日目は変更不可です（コード{current}）"
            )
            continue

        new_code = 0 if new_status == "work" else 1
        old_code = schedule[staff_idx, day_idx]
        schedule[staff_idx, day_idx] = new_code
        applied.append(
            {
                "staff_name": staff_name,
                "day": day,
                "old": "出勤" if old_code == 0 else "休日",
                "new": "出勤" if new_code == 0 else "休日",
            }
        )

    # Run compliance check on adjusted schedule
    from ga_shift.agents.validator import ValidatorAgent
    from ga_shift.models.schedule import ShiftResult

    validator = ValidatorAgent()
    shift_result = ShiftResult(
        best_schedule=schedule,
        best_score=0.0,
        generation_count=0,
    )

    constraint_set = _facility_state.get("custom_constraints")
    if constraint_set:
        cs = ConstraintSet(name="custom", constraints=constraint_set)
    else:
        cs = ConstraintSet.kimachi_default()

    from ga_shift.constraints.registry import get_registry as _get_reg

    registry = _get_reg()
    compiled = registry.compile_set(cs)
    validation = validator.validate(
        shift_result=shift_result,
        shift_input=shift_input,
        constraints=compiled,
    )

    # Write adjusted schedule to Excel
    out = Path(output_path) if output_path else result_file
    wb = openpyxl.load_workbook(result_file)
    ws = wb["シフト表"]

    _DAY_COL_OFFSET = 4
    _DATA_ROW_START = 4  # 0-indexed row 4 = Excel row 5

    for change_info in applied:
        staff_name = change_info["staff_name"]
        day = change_info["day"]
        new_status = change_info["new"]

        for i, emp in enumerate(shift_input.employees):
            if emp.name == staff_name:
                row = _DATA_ROW_START + i + 1  # openpyxl is 1-indexed
                col = _DAY_COL_OFFSET + day  # day is 1-indexed
                ws.cell(row=row, column=col).value = "" if new_status == "出勤" else "休"
                break

    wb.save(out)

    return {
        "status": "ok",
        "applied_changes": applied,
        "errors": errors,
        "output_path": str(out),
        "is_compliant": validation.is_compliant,
        "new_violations": [
            {"constraint": v.constraint_id, "message": v.message}
            for v in validation.violations[:5]
        ],
    }


# ---------------------------------------------------------------------------
# Tool 8: check_compliance
# ---------------------------------------------------------------------------
@mcp.tool
def check_compliance(
    result_path: str,
    constraint_preset: str = "auto",
) -> dict[str, Any]:
    """人員配置基準の充足状況をチェックします。

    Args:
        result_path: シフトExcelファイルのパス
        constraint_preset: 制約プリセット ("auto", "kimachiya", "default")

    Returns:
        充足状況の詳細レポート
    """
    result_file = Path(result_path)
    if not result_file.exists():
        return {"status": "error", "message": f"ファイルが見つかりません: {result_path}"}

    shift_input = read_shift_input(result_file)

    # Determine constraint set
    if constraint_preset == "auto" and "custom_constraints" in _facility_state:
        cs = ConstraintSet(name="custom", constraints=_facility_state["custom_constraints"])
    elif constraint_preset == "kimachiya":
        cs = ConstraintSet.kimachi_default()
    else:
        cs = ConstraintSet.default_set()

    registry = get_registry()
    compiled = registry.compile_set(cs)

    from ga_shift.agents.validator import ValidatorAgent
    from ga_shift.models.schedule import ShiftResult

    validator = ValidatorAgent()
    shift_result = ShiftResult(
        best_schedule=shift_input.base_schedule,
        best_score=0.0,
        generation_count=0,
    )

    validation = validator.validate(
        shift_result=shift_result,
        shift_input=shift_input,
        constraints=compiled,
    )

    return {
        "status": "ok",
        "is_compliant": validation.is_compliant,
        "total_penalty": round(validation.total_penalty, 2),
        "error_count": validation.error_count,
        "warning_count": validation.warning_count,
        "constraint_scores": [
            {
                "constraint": cs.constraint_id,
                "name": cs.constraint_name,
                "penalty": round(cs.penalty, 2),
                "violation_count": len(cs.violations),
            }
            for cs in validation.constraint_scores
        ],
        "violations": [
            {
                "constraint": v.constraint_id,
                "message": v.message,
                "severity": v.severity.value,
                "employee": (
                    shift_input.employees[v.employee_index].name
                    if v.employee_index is not None
                    else None
                ),
                "day": v.day_index + 1 if v.day_index is not None else None,
            }
            for v in validation.violations
        ],
    }


# ---------------------------------------------------------------------------
# Tool 9: import_accompanied_visits
# ---------------------------------------------------------------------------
@mcp.tool
def import_accompanied_visits(
    visits: list[dict[str, Any]],
) -> dict[str, Any]:
    """利用者の通院同行スケジュールをシフト制約として一括登録します.

    support-db（Neo4j）から取得した利用者の通院予定と
    同行スタッフの情報を、GA-shiftの出勤制約に変換します。

    Args:
        visits: 通院同行情報のリスト。各要素は以下の形式:
            {
                "client_name": "山田健太",       # 利用者名
                "staff_name": "川崎聡",          # 同行スタッフ名
                "day": 15,                       # 通院日（1-indexed）
                "visit_type": "定期通院",        # "定期通院" or "臨時通院"
                "hospital": "○○病院",            # 通院先（任意）
                "note": "精神科の定期受診"        # メモ（任意）
            }

    Returns:
        登録結果のサマリー
    """
    if not _facility_state.get("staff"):
        return {
            "status": "error",
            "message": "事業所が未設定です。先に setup_facility を実行してください。",
        }

    registered = []
    errors = []
    staff_names = {s["name"] for s in _facility_state["staff"]}

    for visit in visits:
        staff_name = visit.get("staff_name", "")
        client_name = visit.get("client_name", "")
        day = visit.get("day", 0)
        visit_type = visit.get("visit_type", "通院同行")
        hospital = visit.get("hospital", "")
        note = visit.get("note", "")

        # Validate staff exists in facility
        if staff_name not in staff_names:
            errors.append(
                f"スタッフ '{staff_name}' は事業所に登録されていません"
            )
            continue

        # Validate day
        if day < 1 or day > 31:
            errors.append(f"日付 {day} は範囲外です（1-31）")
            continue

        # Store in facility state as accompanied visit constraint
        if "accompanied_visits" not in _facility_state:
            _facility_state["accompanied_visits"] = []

        visit_record = {
            "client_name": client_name,
            "staff_name": staff_name,
            "day": day,
            "visit_type": visit_type,
            "hospital": hospital,
            "note": note,
            "constraint_type": "must_work",  # 同行日は出勤必須
        }
        _facility_state["accompanied_visits"].append(visit_record)
        registered.append(visit_record)

    return {
        "status": "ok",
        "registered_count": len(registered),
        "error_count": len(errors),
        "registered": [
            {
                "staff": v["staff_name"],
                "client": v["client_name"],
                "day": v["day"],
                "type": v["visit_type"],
            }
            for v in registered
        ],
        "errors": errors,
        "total_accompanied_visits": len(
            _facility_state.get("accompanied_visits", [])
        ),
        "message": (
            f"{len(registered)}件の通院同行をシフト制約に登録しました。"
            if registered
            else "登録できる通院同行がありませんでした。"
        ),
    }


# ---------------------------------------------------------------------------
# Tool 10: get_accompanied_visits
# ---------------------------------------------------------------------------
@mcp.tool
def get_accompanied_visits() -> dict[str, Any]:
    """登録済みの通院同行スケジュールを一覧表示します.

    import_accompanied_visits で登録された通院同行制約の
    一覧を返します。

    Returns:
        登録済み通院同行の一覧
    """
    visits = _facility_state.get("accompanied_visits", [])

    # Group by staff
    by_staff: dict[str, list[dict[str, Any]]] = {}
    for v in visits:
        staff = v["staff_name"]
        if staff not in by_staff:
            by_staff[staff] = []
        by_staff[staff].append(v)

    staff_summary = []
    for staff_name, staff_visits in by_staff.items():
        staff_summary.append(
            {
                "staff_name": staff_name,
                "visit_count": len(staff_visits),
                "days": [v["day"] for v in staff_visits],
                "clients": list({v["client_name"] for v in staff_visits}),
            }
        )

    return {
        "status": "ok",
        "total_visits": len(visits),
        "visits": [
            {
                "staff": v["staff_name"],
                "client": v["client_name"],
                "day": v["day"],
                "type": v["visit_type"],
                "hospital": v.get("hospital", ""),
                "note": v.get("note", ""),
            }
            for v in visits
        ],
        "by_staff": staff_summary,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
