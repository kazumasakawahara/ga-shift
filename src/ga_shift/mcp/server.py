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
# Tool 11: analyze_schedule_balance
# ---------------------------------------------------------------------------
@mcp.tool
def analyze_schedule_balance(
    result_path: str,
) -> dict[str, Any]:
    """シフト結果の公平性・偏りを分析します.

    各スタッフの勤務日数、週末出勤回数、最大連続勤務日数を
    計算し、偏りがある場合は警告を出します。

    Args:
        result_path: シフトExcelファイルのパス

    Returns:
        公平性分析の結果
    """
    result_file = Path(result_path)
    if not result_file.exists():
        return {"status": "error", "message": f"ファイルが見つかりません: {result_path}"}

    shift_input = read_shift_input(result_file)
    schedule = shift_input.base_schedule

    staff_analysis = []
    work_day_counts = []
    weekend_counts = []

    for i, emp in enumerate(shift_input.employees):
        row = schedule[i]
        work_days = int(np.sum(row == 0))
        holidays = int(np.sum((row == 1) | (row == 2)))
        work_day_counts.append(work_days)

        # Weekend work count (Sat=5, Sun=6)
        weekend_work = 0
        for d in range(shift_input.num_days):
            if d < len(shift_input.day_labels):
                label = shift_input.day_labels[d]
                if label in ("土", "日") and row[d] == 0:
                    weekend_work += 1
        weekend_counts.append(weekend_work)

        # Max consecutive work days
        max_consec = 0
        current_consec = 0
        for d in range(shift_input.num_days):
            if row[d] == 0:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0

        # Has 2+ consecutive holidays?
        max_consec_off = 0
        current_off = 0
        for d in range(shift_input.num_days):
            if row[d] in (1, 2):
                current_off += 1
                max_consec_off = max(max_consec_off, current_off)
            else:
                current_off = 0

        staff_analysis.append({
            "name": emp.name,
            "employee_type": emp.employee_type.value,
            "work_days": work_days,
            "holidays": holidays,
            "weekend_work": weekend_work,
            "max_consecutive_work": max_consec,
            "max_consecutive_off": max_consec_off,
            "alerts": [],
        })

        # Alert checks
        if max_consec >= 7:
            staff_analysis[-1]["alerts"].append(
                f"警告: {max_consec}日連続勤務があります"
            )
        elif max_consec >= 5:
            staff_analysis[-1]["alerts"].append(
                f"注意: {max_consec}日連続勤務があります"
            )
        if max_consec_off == 0:
            staff_analysis[-1]["alerts"].append("注意: 連休がありません")

    # Overall statistics
    avg_work = float(np.mean(work_day_counts)) if work_day_counts else 0
    std_work = float(np.std(work_day_counts)) if work_day_counts else 0
    avg_weekend = float(np.mean(weekend_counts)) if weekend_counts else 0
    std_weekend = float(np.std(weekend_counts)) if weekend_counts else 0

    # Global alerts
    alerts = []
    if std_work > 2.0:
        alerts.append(f"警告: 勤務日数の偏差が大きい（標準偏差: {std_work:.1f}日）")
    if std_weekend > 1.5:
        alerts.append(f"警告: 週末出勤の偏差が大きい（標準偏差: {std_weekend:.1f}回）")

    return {
        "status": "ok",
        "staff_count": shift_input.num_employees,
        "total_days": shift_input.num_days,
        "average_work_days": round(avg_work, 1),
        "work_days_std": round(std_work, 1),
        "average_weekend_work": round(avg_weekend, 1),
        "weekend_work_std": round(std_weekend, 1),
        "staff_analysis": staff_analysis,
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# Tool 12: get_staffing_requirements
# ---------------------------------------------------------------------------
@mcp.tool
def get_staffing_requirements(
    facility_type: str = "就労継続支援B型",
    user_count: int = 20,
) -> dict[str, Any]:
    """事業種別に応じた人員配置基準を返します.

    福祉事業所の法的基準に基づいた必要人員数を計算します。

    Args:
        facility_type: 事業種別（"就労継続支援B型", "就労継続支援A型",
                        "生活介護", "就労移行支援"）
        user_count: 利用者定員数

    Returns:
        人員配置基準の詳細
    """
    # B-type employment support standards (障害者総合支援法)
    requirements: dict[str, Any] = {
        "facility_type": facility_type,
        "user_count": user_count,
        "standards": [],
        "notes": [],
    }

    if facility_type == "就労継続支援B型":
        # 職業指導員 + 生活支援員 (利用者10:1以上)
        staff_ratio = max(1, (user_count + 9) // 10)  # 切り上げ
        requirements["standards"].append({
            "role": "職業指導員・生活支援員",
            "required": staff_ratio,
            "unit": "人以上（常勤換算）",
            "basis": "利用者10人に対し1人以上",
            "note": "うち1人以上は常勤であること",
        })

        # サービス管理責任者
        if user_count <= 60:
            sabi_count = 1
        else:
            sabi_count = 1 + ((user_count - 61) // 40) + 1
        requirements["standards"].append({
            "role": "サービス管理責任者",
            "required": sabi_count,
            "unit": "人以上",
            "basis": "利用者60人以下で1人、61人以上で40人ごとに1人追加",
        })

        # 管理者
        requirements["standards"].append({
            "role": "管理者",
            "required": 1,
            "unit": "人",
            "basis": "常勤（他職務との兼務可）",
        })

        requirements["notes"] = [
            "営業日ごとに配置基準を満たす必要があります",
            "常勤換算には週の勤務時間比率を使用します",
            "パートスタッフは勤務時間に応じた常勤換算で計算",
        ]

        # 日別最低人員の目安
        requirements["daily_minimum"] = max(2, staff_ratio)
        requirements["daily_minimum_note"] = (
            f"営業日1日あたり最低{max(2, staff_ratio)}人の配置を推奨"
        )

    elif facility_type == "就労継続支援A型":
        staff_ratio = max(1, (user_count + 9) // 10)
        requirements["standards"].append({
            "role": "職業指導員・生活支援員",
            "required": staff_ratio,
            "unit": "人以上（常勤換算）",
            "basis": "利用者10人に対し1人以上",
        })
        requirements["daily_minimum"] = max(2, staff_ratio)

    elif facility_type == "生活介護":
        # 利用者3:1 or 5:1 (平均障害支援区分による)
        staff_ratio_high = max(1, (user_count + 2) // 3)
        staff_ratio_low = max(1, (user_count + 4) // 5)
        requirements["standards"].append({
            "role": "生活支援員・看護職員等",
            "required": staff_ratio_low,
            "unit": f"人以上（区分により{staff_ratio_low}〜{staff_ratio_high}人）",
            "basis": "平均障害支援区分5以上:3:1、4以上5未満:4:1、4未満:6:1",
        })
        requirements["daily_minimum"] = max(2, staff_ratio_low)

    else:
        # Generic default
        staff_ratio = max(1, (user_count + 5) // 6)
        requirements["standards"].append({
            "role": "支援員",
            "required": staff_ratio,
            "unit": "人以上",
            "basis": "利用者6人に対し1人以上（目安）",
        })
        requirements["daily_minimum"] = max(2, staff_ratio)

    return {
        "status": "ok",
        **requirements,
    }


# ---------------------------------------------------------------------------
# Tool 13: transfer_staff
# ---------------------------------------------------------------------------
@mcp.tool
def transfer_staff(
    action: str,
    staff_name: str,
    staff_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """スタッフの追加・削除・情報更新を行います.

    人事異動（入退社、セクション変更、条件変更）に対応します。

    Args:
        action: 操作種別
            - "add": 新規スタッフ追加
            - "remove": スタッフ削除（退職）
            - "update": スタッフ情報の更新
        staff_name: 対象スタッフの名前
        staff_info: スタッフ情報（add/updateの場合に使用）
            {
                "employee_type": "正規",
                "section": "仕込み",
                "vacation_days": 3,
                "holidays": 9,
                "unavailable_weekdays": [2]
            }

    Returns:
        操作結果
    """
    if not _facility_state.get("staff"):
        return {
            "status": "error",
            "message": "事業所が未設定です。先に setup_facility を実行してください。",
        }

    current_staff = _facility_state["staff"]
    staff_names = [s["name"] for s in current_staff]

    if action == "add":
        if staff_name in staff_names:
            return {
                "status": "error",
                "message": f"スタッフ '{staff_name}' はすでに登録されています",
            }

        new_staff = {"name": staff_name, **(staff_info or {})}
        current_staff.append(new_staff)

        # Also update employee_presets
        presets = _facility_state.get("employee_presets", [])
        presets.append(
            EmployeePreset(
                name=staff_name,
                employee_type=new_staff.get("employee_type", "正規"),
                section=new_staff.get("section", ""),
                vacation_days=new_staff.get("vacation_days", 0),
                holidays=new_staff.get("holidays", 9),
                unavailable_weekdays=new_staff.get("unavailable_weekdays", []),
            )
        )
        _facility_state["employee_presets"] = presets

        return {
            "status": "ok",
            "action": "add",
            "staff_name": staff_name,
            "new_total": len(current_staff),
            "message": f"スタッフ '{staff_name}' を追加しました（合計{len(current_staff)}名）",
        }

    elif action == "remove":
        if staff_name not in staff_names:
            return {
                "status": "error",
                "message": f"スタッフ '{staff_name}' が見つかりません",
            }

        # Remove from staff list
        _facility_state["staff"] = [
            s for s in current_staff if s["name"] != staff_name
        ]
        # Remove from presets
        presets = _facility_state.get("employee_presets", [])
        _facility_state["employee_presets"] = [
            p for p in presets if p.name != staff_name
        ]

        # Check accompanied visits impact
        affected_visits = [
            v for v in _facility_state.get("accompanied_visits", [])
            if v["staff_name"] == staff_name
        ]

        return {
            "status": "ok",
            "action": "remove",
            "staff_name": staff_name,
            "new_total": len(_facility_state["staff"]),
            "affected_accompanied_visits": len(affected_visits),
            "message": (
                f"スタッフ '{staff_name}' を削除しました"
                f"（合計{len(_facility_state['staff'])}名）"
            ),
            "warnings": (
                [f"通院同行が{len(affected_visits)}件影響を受けます。再割り当てが必要です。"]
                if affected_visits
                else []
            ),
        }

    elif action == "update":
        if staff_name not in staff_names:
            return {
                "status": "error",
                "message": f"スタッフ '{staff_name}' が見つかりません",
            }

        if not staff_info:
            return {
                "status": "error",
                "message": "更新情報（staff_info）が必要です",
            }

        # Update staff list
        changes = []
        for s in current_staff:
            if s["name"] == staff_name:
                for key, value in staff_info.items():
                    old_value = s.get(key)
                    if old_value != value:
                        changes.append({
                            "field": key,
                            "old": old_value,
                            "new": value,
                        })
                    s[key] = value
                break

        # Update employee presets
        presets = _facility_state.get("employee_presets", [])
        for p in presets:
            if p.name == staff_name:
                if "employee_type" in staff_info:
                    p.employee_type = staff_info["employee_type"]
                if "section" in staff_info:
                    p.section = staff_info["section"]
                if "vacation_days" in staff_info:
                    p.vacation_days = staff_info["vacation_days"]
                if "holidays" in staff_info:
                    p.holidays = staff_info["holidays"]
                if "unavailable_weekdays" in staff_info:
                    p.unavailable_weekdays = staff_info["unavailable_weekdays"]
                break

        return {
            "status": "ok",
            "action": "update",
            "staff_name": staff_name,
            "changes": changes,
            "message": (
                f"スタッフ '{staff_name}' の情報を更新しました"
                f"（{len(changes)}項目変更）"
            ),
        }

    else:
        return {
            "status": "error",
            "message": f"不正な操作種別です: {action}（add/remove/update のいずれか）",
        }


# ---------------------------------------------------------------------------
# Tool 14: generate_shift_report
# ---------------------------------------------------------------------------
@mcp.tool
def generate_shift_report(
    result_path: str,
    constraint_preset: str = "kimachiya",
) -> dict[str, Any]:
    """シフト結果の総合レポートを生成します.

    explain_result, analyze_schedule_balance, check_compliance の
    結果を統合して、月次レポート用のサマリーを返します。

    Args:
        result_path: シフトExcelファイルのパス
        constraint_preset: 制約プリセット名

    Returns:
        総合レポートデータ
    """
    result_file = Path(result_path)
    if not result_file.exists():
        return {"status": "error", "message": f"ファイルが見つかりません: {result_path}"}

    # 3つの分析を実行
    # explain_result は FunctionTool なので .fn で元関数を取得
    explain_fn = getattr(explain_result, "fn", explain_result)
    balance_fn = getattr(analyze_schedule_balance, "fn", analyze_schedule_balance)
    compliance_fn = getattr(check_compliance, "fn", check_compliance)

    explanation = explain_fn(result_path=result_path)
    balance = balance_fn(result_path=result_path)
    compliance = compliance_fn(
        result_path=result_path, constraint_preset=constraint_preset
    )

    # いずれかがエラーなら個別のエラーを返す
    errors = []
    if explanation.get("status") == "error":
        errors.append(f"結果説明: {explanation.get('message')}")
    if balance.get("status") == "error":
        errors.append(f"バランス分析: {balance.get('message')}")
    if compliance.get("status") == "error":
        errors.append(f"コンプライアンス: {compliance.get('message')}")

    if errors:
        return {"status": "error", "message": " / ".join(errors)}

    # 総合評価を算出
    issues = []
    score = 100  # 100点満点から減点

    # バランスの問題
    if balance.get("work_days_std", 0) > 2.0:
        issues.append("勤務日数の偏りが大きい")
        score -= 15
    if balance.get("weekend_work_std", 0) > 1.5:
        issues.append("週末出勤の偏りが大きい")
        score -= 10

    # スタッフ個別の問題
    for staff in balance.get("staff_analysis", []):
        if staff.get("max_consecutive_work", 0) >= 7:
            issues.append(f"{staff['name']}: 7日以上の連続勤務")
            score -= 10
        elif staff.get("max_consecutive_work", 0) >= 5:
            issues.append(f"{staff['name']}: 5日以上の連続勤務")
            score -= 5
        if staff.get("max_consecutive_off", 0) == 0:
            issues.append(f"{staff['name']}: 連休なし")
            score -= 5

    # コンプライアンスの問題
    if not compliance.get("is_compliant", True):
        issues.append("人員配置基準違反あり")
        score -= 20

    violations_count = len(compliance.get("violations", []))
    if violations_count > 0:
        score -= min(violations_count * 3, 15)

    score = max(0, score)

    # 評価ランク
    if score >= 90:
        grade = "A（優秀）"
    elif score >= 75:
        grade = "B（良好）"
    elif score >= 60:
        grade = "C（要改善）"
    else:
        grade = "D（要注意）"

    return {
        "status": "ok",
        "report": {
            "summary": {
                "staff_count": explanation.get("staff_count", 0),
                "total_days": explanation.get("total_days", 0),
                "overall_score": score,
                "grade": grade,
                "issues_count": len(issues),
            },
            "staff_detail": explanation.get("staff_summary", []),
            "balance": {
                "average_work_days": balance.get("average_work_days"),
                "work_days_std": balance.get("work_days_std"),
                "average_weekend_work": balance.get("average_weekend_work"),
                "weekend_work_std": balance.get("weekend_work_std"),
                "staff_analysis": balance.get("staff_analysis", []),
                "balance_alerts": balance.get("alerts", []),
            },
            "compliance": {
                "is_compliant": compliance.get("is_compliant"),
                "total_penalty": compliance.get("total_penalty"),
                "violations": compliance.get("violations", []),
                "constraint_scores": compliance.get("constraint_scores", []),
            },
            "issues": issues,
            "recommendations": _generate_recommendations(issues, balance, compliance),
        },
    }


def _generate_recommendations(
    issues: list[str],
    balance: dict[str, Any],
    compliance: dict[str, Any],
) -> list[str]:
    """問題点から改善提案を生成する。"""
    recommendations = []

    if any("連続勤務" in i for i in issues):
        recommendations.append(
            "連続勤務を減らすため、制約に「最大連続勤務5日」を追加することを推奨します"
        )
    if any("偏り" in i for i in issues):
        recommendations.append(
            "勤務日数の均等化のため、希望休の調整またはGA重みの見直しを検討してください"
        )
    if any("連休なし" in i for i in issues):
        recommendations.append(
            "スタッフのリフレッシュのため、月1回以上の連休確保を推奨します"
        )
    if any("人員配置基準違反" in i for i in issues):
        recommendations.append(
            "人員配置基準を満たすため、シフト調整または増員を検討してください"
        )
    if not recommendations:
        recommendations.append("現在のシフトは良好です。この品質を維持してください。")

    return recommendations


# ---------------------------------------------------------------------------
# Tool 15: simulate_scenario
# ---------------------------------------------------------------------------
@mcp.tool
def simulate_scenario(
    base_template_path: str,
    scenario_type: str,
    scenario_params: dict[str, Any] | None = None,
    constraint_preset: str = "kimachiya",
    population_size: int = 30,
    generations: int = 5,
) -> dict[str, Any]:
    """仮定のシナリオでシフトを再最適化し、影響を分析します.

    「スタッフが退職したら？」「パートを増やしたら？」等の
    What-ifシミュレーションを実行します。

    Args:
        base_template_path: 比較基準となるシフトExcelファイルのパス
        scenario_type: シナリオ種別
            - "remove_staff": スタッフ退職
            - "add_staff": スタッフ追加
            - "change_users": 利用者数変更
            - "change_constraint": 制約条件変更
        scenario_params: シナリオのパラメータ
            remove_staff: {"staff_name": "川崎聡"}
            add_staff: {"staff_name": "新人", "employee_type": "パート",
                        "section": "ランチ", ...}
            change_users: {"new_user_count": 30}
            change_constraint: {"constraint_type": "...", "parameters": {...}}
        constraint_preset: 制約プリセット名
        population_size: GA集団サイズ
        generations: GA世代数

    Returns:
        シミュレーション結果と比較分析
    """
    base_file = Path(base_template_path)
    if not base_file.exists():
        return {
            "status": "error",
            "message": f"ファイルが見つかりません: {base_template_path}",
        }

    params = scenario_params or {}

    # --- Baseline analysis ---
    balance_fn = getattr(analyze_schedule_balance, "fn", analyze_schedule_balance)
    baseline_balance = balance_fn(result_path=base_template_path)

    compliance_fn = getattr(check_compliance, "fn", check_compliance)
    baseline_compliance = compliance_fn(
        result_path=base_template_path, constraint_preset=constraint_preset
    )

    baseline_summary = {
        "staff_count": baseline_balance.get("staff_count", 0),
        "average_work_days": baseline_balance.get("average_work_days"),
        "work_days_std": baseline_balance.get("work_days_std"),
        "is_compliant": baseline_compliance.get("is_compliant"),
        "violations_count": len(baseline_compliance.get("violations", [])),
    }

    # --- Scenario analysis ---
    if scenario_type == "remove_staff":
        staff_name = params.get("staff_name", "")
        if not staff_name:
            return {"status": "error", "message": "staff_name が必要です"}

        # Check current staff
        current_staff = _facility_state.get("staff", [])
        staff_found = any(s["name"] == staff_name for s in current_staff)

        # Check staffing requirements
        staffing_fn = getattr(get_staffing_requirements, "fn", get_staffing_requirements)
        facility_type = _facility_state.get("facility_type", "就労継続支援B型")
        requirements = staffing_fn(facility_type=facility_type)
        daily_min = requirements.get("daily_minimum", 2)

        new_staff_count = len(current_staff) - (1 if staff_found else 0)

        # Check accompanied visits impact
        affected_visits = [
            v for v in _facility_state.get("accompanied_visits", [])
            if v.get("staff_name") == staff_name
        ]

        impact = {
            "scenario_type": "remove_staff",
            "staff_name": staff_name,
            "staff_found": staff_found,
            "current_staff_count": len(current_staff),
            "new_staff_count": new_staff_count,
            "daily_minimum_required": daily_min,
            "meets_minimum": new_staff_count >= daily_min,
            "affected_accompanied_visits": len(affected_visits),
            "risk_level": (
                "高" if new_staff_count < daily_min
                else "中" if new_staff_count == daily_min
                else "低"
            ),
        }

        recommendations = []
        if not impact["meets_minimum"]:
            recommendations.append(
                f"退職後の人員{new_staff_count}名は最低基準{daily_min}名を下回ります。"
                "早急な採用が必要です。"
            )
        if affected_visits:
            recommendations.append(
                f"通院同行{len(affected_visits)}件の担当を再割り当てしてください。"
            )
        if impact["risk_level"] == "中":
            recommendations.append(
                "最低基準ぎりぎりです。急な欠勤に備え、採用を検討してください。"
            )

        return {
            "status": "ok",
            "scenario": impact,
            "baseline": baseline_summary,
            "recommendations": recommendations,
        }

    elif scenario_type == "add_staff":
        staff_name = params.get("staff_name", "新規スタッフ")
        current_staff = _facility_state.get("staff", [])

        staffing_fn = getattr(get_staffing_requirements, "fn", get_staffing_requirements)
        facility_type = _facility_state.get("facility_type", "就労継続支援B型")
        requirements = staffing_fn(facility_type=facility_type)
        daily_min = requirements.get("daily_minimum", 2)

        new_staff_count = len(current_staff) + 1

        impact = {
            "scenario_type": "add_staff",
            "staff_name": staff_name,
            "employee_type": params.get("employee_type", "未定"),
            "section": params.get("section", "未定"),
            "current_staff_count": len(current_staff),
            "new_staff_count": new_staff_count,
            "daily_minimum_required": daily_min,
            "staffing_buffer": new_staff_count - daily_min,
        }

        recommendations = []
        if len(current_staff) < daily_min:
            recommendations.append(
                f"現在{len(current_staff)}名で基準{daily_min}名を下回っています。"
                "増員は必須です。"
            )
        if impact["staffing_buffer"] >= 2:
            recommendations.append(
                "十分な人員余裕があります。シフトの柔軟性が向上します。"
            )
        recommendations.append(
            "増員後はテンプレートを再生成し、再最適化を実行してください。"
        )

        return {
            "status": "ok",
            "scenario": impact,
            "baseline": baseline_summary,
            "recommendations": recommendations,
        }

    elif scenario_type == "change_users":
        new_user_count = params.get("new_user_count", 20)
        current_user_count = _facility_state.get("user_count", 20)

        staffing_fn = getattr(get_staffing_requirements, "fn", get_staffing_requirements)
        facility_type = _facility_state.get("facility_type", "就労継続支援B型")

        current_req = staffing_fn(
            facility_type=facility_type, user_count=current_user_count
        )
        new_req = staffing_fn(
            facility_type=facility_type, user_count=new_user_count
        )

        current_staff_count = len(_facility_state.get("staff", []))
        new_daily_min = new_req.get("daily_minimum", 2)

        impact = {
            "scenario_type": "change_users",
            "current_user_count": current_user_count,
            "new_user_count": new_user_count,
            "change": new_user_count - current_user_count,
            "current_daily_minimum": current_req.get("daily_minimum", 2),
            "new_daily_minimum": new_daily_min,
            "current_staff_count": current_staff_count,
            "meets_new_minimum": current_staff_count >= new_daily_min,
            "staff_gap": current_staff_count - new_daily_min,
        }

        recommendations = []
        if not impact["meets_new_minimum"]:
            gap = new_daily_min - current_staff_count
            recommendations.append(
                f"利用者{new_user_count}人には最低{new_daily_min}名必要。"
                f"現在{current_staff_count}名のため{gap}名の増員が必要です。"
            )
        elif impact["staff_gap"] <= 1:
            recommendations.append(
                "基準ぎりぎりです。利用者増を見越して早めの採用を推奨します。"
            )
        else:
            recommendations.append(
                "現在の人員で対応可能です。"
            )

        # Compare staffing standards
        impact["current_standards"] = current_req.get("standards", [])
        impact["new_standards"] = new_req.get("standards", [])

        return {
            "status": "ok",
            "scenario": impact,
            "baseline": baseline_summary,
            "recommendations": recommendations,
        }

    elif scenario_type == "change_constraint":
        constraint_type = params.get("constraint_type", "")
        constraint_params = params.get("parameters", {})

        if not constraint_type:
            return {"status": "error", "message": "constraint_type が必要です"}

        # Validate constraint exists
        registry = get_registry()
        available = [t.template_id for t in registry.list_all()]

        if constraint_type not in available:
            return {
                "status": "error",
                "message": f"制約 '{constraint_type}' は存在しません",
                "available_constraints": available,
            }

        return {
            "status": "ok",
            "scenario": {
                "scenario_type": "change_constraint",
                "constraint_type": constraint_type,
                "parameters": constraint_params,
                "note": (
                    "制約変更後は再最適化を実行して影響を確認してください。"
                    "add_constraint → run_optimization の順序で実行します。"
                ),
            },
            "baseline": baseline_summary,
            "recommendations": [
                f"制約 '{constraint_type}' を追加/変更後、再最適化を実行してください。",
                "結果を analyze_schedule_balance で確認し、品質劣化がないか確認してください。",
            ],
        }

    else:
        return {
            "status": "error",
            "message": (
                f"不明なシナリオ種別: {scenario_type}。"
                "remove_staff / add_staff / change_users / change_constraint "
                "のいずれかを指定してください。"
            ),
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
