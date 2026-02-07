"""MCPツールの単体テスト.

各ツール関数をPythonから直接呼び出してテストする。
MCPプロトコルを介さないため高速。

NOTE: FastMCPの @mcp.tool デコレータは FunctionTool オブジェクトを返す。
元の関数には .fn 属性でアクセスする。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from ga_shift.io.template_generator import generate_kimachiya_template
from ga_shift.mcp.server import (
    _facility_state,
    add_constraint as _add_constraint_tool,
    adjust_schedule as _adjust_schedule_tool,
    analyze_schedule_balance as _analyze_schedule_balance_tool,
    check_compliance as _check_compliance_tool,
    explain_result as _explain_result_tool,
    generate_shift_report as _generate_shift_report_tool,
    generate_shift_template as _generate_shift_template_tool,
    get_accompanied_visits as _get_accompanied_visits_tool,
    get_staffing_requirements as _get_staffing_requirements_tool,
    import_accompanied_visits as _import_accompanied_visits_tool,
    list_constraints as _list_constraints_tool,
    run_optimization as _run_optimization_tool,
    setup_facility as _setup_facility_tool,
    simulate_scenario as _simulate_scenario_tool,
    transfer_staff as _transfer_staff_tool,
)

# FunctionTool → 元の関数を取得
def _unwrap(tool):
    """FastMCP FunctionTool から元の関数を取り出す。"""
    return getattr(tool, "fn", tool)

setup_facility = _unwrap(_setup_facility_tool)
add_constraint = _unwrap(_add_constraint_tool)
list_constraints = _unwrap(_list_constraints_tool)
generate_shift_template = _unwrap(_generate_shift_template_tool)
run_optimization = _unwrap(_run_optimization_tool)
explain_result = _unwrap(_explain_result_tool)
adjust_schedule = _unwrap(_adjust_schedule_tool)
check_compliance = _unwrap(_check_compliance_tool)
import_accompanied_visits = _unwrap(_import_accompanied_visits_tool)
get_accompanied_visits = _unwrap(_get_accompanied_visits_tool)
analyze_schedule_balance = _unwrap(_analyze_schedule_balance_tool)
get_staffing_requirements = _unwrap(_get_staffing_requirements_tool)
transfer_staff = _unwrap(_transfer_staff_tool)
generate_shift_report = _unwrap(_generate_shift_report_tool)
simulate_scenario = _unwrap(_simulate_scenario_tool)


# ---------------------------------------------------------------------------
# Fixture: 毎テストで facility_state をリセット
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_facility_state():
    """各テストの前後で _facility_state をクリアする。"""
    _facility_state.clear()
    yield
    _facility_state.clear()


@pytest.fixture
def kimachiya_staff() -> list[dict]:
    """木町家の5名スタッフ定義。"""
    return [
        {
            "name": "川崎聡",
            "employee_type": "正規",
            "section": "仕込み",
            "vacation_days": 3,
            "holidays": 9,
            "unavailable_weekdays": [],
        },
        {
            "name": "斎藤駿児",
            "employee_type": "正規",
            "section": "仕込み・ランチ",
            "vacation_days": 3,
            "holidays": 9,
            "unavailable_weekdays": [],
        },
        {
            "name": "平田園美",
            "employee_type": "パート",
            "section": "仕込み",
            "vacation_days": 2,
            "holidays": 9,
            "unavailable_weekdays": [],
        },
        {
            "name": "島村誠",
            "employee_type": "正規",
            "section": "ランチ",
            "vacation_days": 3,
            "holidays": 9,
            "unavailable_weekdays": [2],  # 水曜
        },
        {
            "name": "橋本由紀",
            "employee_type": "パート",
            "section": "ランチ",
            "vacation_days": 2,
            "holidays": 9,
            "unavailable_weekdays": [],
        },
    ]


@pytest.fixture
def kimachiya_template_path() -> Path:
    """木町家テンプレートExcelを生成して返す。テスト後に削除。"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        tmppath = Path(f.name)
    generate_kimachiya_template(str(tmppath), 2026, 3)
    yield tmppath
    tmppath.unlink(missing_ok=True)


# ===================================================================
# Tool 1: setup_facility
# ===================================================================
class TestSetupFacility:
    def test_basic_setup(self, kimachiya_staff):
        """基本的な事業所設定が成功すること。"""
        result = setup_facility(
            name="木町家",
            facility_type="就労継続支援B型",
            sections=["仕込み", "ランチ", "ホール"],
            staff=kimachiya_staff,
        )

        assert result["status"] == "ok"
        assert result["facility_name"] == "木町家"
        assert result["staff_count"] == 5
        assert "川崎聡" in result["staff_names"]
        assert "島村誠" in result["staff_names"]

    def test_setup_stores_state(self, kimachiya_staff):
        """設定が _facility_state に保存されること。"""
        setup_facility(name="テスト事業所", staff=kimachiya_staff)

        assert _facility_state["name"] == "テスト事業所"
        assert len(_facility_state["employee_presets"]) == 5

    def test_setup_without_staff(self):
        """スタッフなしでも設定が成功すること。"""
        result = setup_facility(name="空の事業所")

        assert result["status"] == "ok"
        assert result["staff_count"] == 0

    def test_setup_with_output_dir(self):
        """output_dir を指定して設定できること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = setup_facility(name="テスト", output_dir=tmpdir)
            assert result["status"] == "ok"
            assert _facility_state["output_dir"] == tmpdir


# ===================================================================
# Tool 2: add_constraint
# ===================================================================
class TestAddConstraint:
    def test_add_valid_constraint(self):
        """有効な制約テンプレートを追加できること。"""
        result = add_constraint(
            constraint_type="kitchen_min_workers",
            parameters={"min_kitchen_workers": 3, "weight": 50},
        )

        assert result["status"] == "ok"
        assert result["constraint_type"] == "kitchen_min_workers"
        assert result["total_custom_constraints"] == 1

    def test_add_multiple_constraints(self):
        """複数の制約を追加できること。"""
        add_constraint(constraint_type="kitchen_min_workers")
        result = add_constraint(constraint_type="substitute_constraint")

        assert result["total_custom_constraints"] == 2

    def test_add_invalid_constraint(self):
        """存在しない制約テンプレートでエラーが返ること。"""
        result = add_constraint(constraint_type="nonexistent_constraint")

        assert result["status"] == "error"
        assert "available_constraints" in result

    def test_add_disabled_constraint(self):
        """無効状態の制約を追加できること。"""
        result = add_constraint(
            constraint_type="kitchen_min_workers",
            enabled=False,
        )
        assert result["status"] == "ok"


# ===================================================================
# Tool 3: list_constraints
# ===================================================================
class TestListConstraints:
    def test_list_returns_all_templates(self):
        """全制約テンプレートが返されること。"""
        result = list_constraints()

        assert result["count"] > 0
        assert len(result["constraints"]) == result["count"]

    def test_list_has_required_fields(self):
        """各制約テンプレートに必須フィールドがあること。"""
        result = list_constraints()

        for c in result["constraints"]:
            assert "template_id" in c
            assert "name_ja" in c
            assert "category" in c
            assert "parameters" in c

    def test_list_includes_kimachi_constraints(self):
        """木町家専用制約がリストに含まれること。"""
        result = list_constraints()
        template_ids = [c["template_id"] for c in result["constraints"]]

        assert "kitchen_min_workers" in template_ids
        assert "substitute_constraint" in template_ids
        assert "unavailable_day_hard" in template_ids


# ===================================================================
# Tool 4: generate_shift_template
# ===================================================================
class TestGenerateShiftTemplate:
    def test_generate_with_staff(self, kimachiya_staff):
        """スタッフ設定済みでテンプレートが生成されること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = generate_shift_template(year=2026, month=3)

        assert result["status"] == "ok"
        assert result["year"] == 2026
        assert result["month"] == 3
        assert result["staff_count"] == 5
        assert Path(result["filepath"]).exists()

        # Cleanup
        Path(result["filepath"]).unlink(missing_ok=True)

    def test_generate_without_staff(self):
        """スタッフ未設定でもデフォルト人数で生成されること。"""
        setup_facility(name="テスト事業所")
        result = generate_shift_template(year=2026, month=4)

        assert result["status"] == "ok"
        assert Path(result["filepath"]).exists()

        Path(result["filepath"]).unlink(missing_ok=True)

    def test_generate_custom_filename(self, kimachiya_staff):
        """カスタムファイル名で生成されること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = generate_shift_template(
            year=2026, month=3, output_filename="custom_test.xlsx"
        )

        assert result["status"] == "ok"
        assert "custom_test.xlsx" in result["filepath"]

        Path(result["filepath"]).unlink(missing_ok=True)


# ===================================================================
# Tool 5: run_optimization
# ===================================================================
class TestRunOptimization:
    def test_optimization_basic(self, kimachiya_template_path):
        """基本的な最適化が成功すること。"""
        result = run_optimization(
            input_path=str(kimachiya_template_path),
            constraint_preset="kimachiya",
            population_size=20,
            generations=3,
        )

        assert result["status"] == "ok"
        assert "best_score" in result
        assert "is_compliant" in result
        assert result["generations"] == 3
        assert len(result["work_days_per_staff"]) > 0

        # Cleanup output
        if "output_path" in result:
            Path(result["output_path"]).unlink(missing_ok=True)

    def test_optimization_nonexistent_file(self):
        """存在しないファイルでエラーが返ること。"""
        result = run_optimization(input_path="/nonexistent/file.xlsx")

        assert result["status"] == "error"
        assert "見つかりません" in result["message"]

    def test_optimization_default_preset(self, kimachiya_template_path):
        """defaultプリセットでも動作すること。"""
        result = run_optimization(
            input_path=str(kimachiya_template_path),
            constraint_preset="default",
            population_size=10,
            generations=2,
        )

        assert result["status"] == "ok"

        if "output_path" in result:
            Path(result["output_path"]).unlink(missing_ok=True)


# ===================================================================
# Tool 6: explain_result
# ===================================================================
class TestExplainResult:
    def test_explain_template(self, kimachiya_template_path):
        """テンプレートファイルの説明が返されること。"""
        result = explain_result(result_path=str(kimachiya_template_path))

        assert result["status"] == "ok"
        assert result["staff_count"] > 0
        assert result["total_days"] > 0
        assert len(result["staff_summary"]) == result["staff_count"]
        assert len(result["daily_staffing"]) == result["total_days"]

    def test_explain_staff_detail(self, kimachiya_template_path):
        """スタッフ詳細に必須フィールドがあること。"""
        result = explain_result(result_path=str(kimachiya_template_path))

        for staff in result["staff_summary"]:
            assert "name" in staff
            assert "work_days" in staff
            assert "holidays" in staff
            assert "off_day_numbers" in staff

    def test_explain_nonexistent_file(self):
        """存在しないファイルでエラーが返ること。"""
        result = explain_result(result_path="/nonexistent/file.xlsx")

        assert result["status"] == "error"


# ===================================================================
# Tool 7: adjust_schedule
# ===================================================================
class TestAdjustSchedule:
    def test_adjust_nonexistent_file(self):
        """存在しないファイルでエラーが返ること。"""
        result = adjust_schedule(
            result_path="/nonexistent/file.xlsx",
            changes=[{"staff_name": "川崎聡", "day": 1, "new_status": "off"}],
        )
        assert result["status"] == "error"

    def test_adjust_invalid_staff(self, kimachiya_template_path):
        """存在しないスタッフ名でエラーが返ること。"""
        # テンプレートファイルは「シフト表」シートを持っているのでそのまま使える
        result = adjust_schedule(
            result_path=str(kimachiya_template_path),
            changes=[{"staff_name": "存在しない人", "day": 1, "new_status": "off"}],
        )
        assert result["status"] == "ok"  # status is ok but errors list has entry
        assert len(result["errors"]) > 0


# ===================================================================
# Tool 8: check_compliance
# ===================================================================
class TestCheckCompliance:
    def test_compliance_check(self, kimachiya_template_path):
        """コンプライアンスチェックが実行できること。"""
        result = check_compliance(
            result_path=str(kimachiya_template_path),
            constraint_preset="kimachiya",
        )

        assert result["status"] == "ok"
        assert "is_compliant" in result
        assert "total_penalty" in result
        assert "constraint_scores" in result
        assert "violations" in result

    def test_compliance_default_preset(self, kimachiya_template_path):
        """defaultプリセットでチェックが動作すること。"""
        result = check_compliance(
            result_path=str(kimachiya_template_path),
            constraint_preset="default",
        )
        assert result["status"] == "ok"

    def test_compliance_nonexistent_file(self):
        """存在しないファイルでエラーが返ること。"""
        result = check_compliance(result_path="/nonexistent/file.xlsx")

        assert result["status"] == "error"

    def test_compliance_violation_structure(self, kimachiya_template_path):
        """violations の各要素に必須フィールドがあること。"""
        result = check_compliance(
            result_path=str(kimachiya_template_path),
            constraint_preset="kimachiya",
        )

        for v in result["violations"]:
            assert "constraint" in v
            assert "message" in v
            assert "severity" in v


# ===================================================================
# Tool 9: import_accompanied_visits
# ===================================================================
class TestImportAccompaniedVisits:
    def test_import_without_facility(self):
        """事業所未設定でエラーが返ること。"""
        result = import_accompanied_visits(
            visits=[{
                "client_name": "山田健太",
                "staff_name": "川崎聡",
                "day": 15,
                "visit_type": "定期通院",
            }]
        )
        assert result["status"] == "error"
        assert "事業所が未設定" in result["message"]

    def test_import_basic(self, kimachiya_staff):
        """基本的な通院同行の登録ができること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = import_accompanied_visits(
            visits=[{
                "client_name": "山田健太",
                "staff_name": "川崎聡",
                "day": 15,
                "visit_type": "定期通院",
                "hospital": "○○病院",
                "note": "精神科の定期受診",
            }]
        )
        assert result["status"] == "ok"
        assert result["registered_count"] == 1
        assert result["error_count"] == 0
        assert result["total_accompanied_visits"] == 1

    def test_import_multiple_visits(self, kimachiya_staff):
        """複数の通院同行を一括登録できること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = import_accompanied_visits(
            visits=[
                {
                    "client_name": "山田健太",
                    "staff_name": "川崎聡",
                    "day": 10,
                    "visit_type": "定期通院",
                },
                {
                    "client_name": "佐藤花子",
                    "staff_name": "斎藤駿児",
                    "day": 15,
                    "visit_type": "臨時通院",
                },
                {
                    "client_name": "田中一郎",
                    "staff_name": "平田園美",
                    "day": 20,
                    "visit_type": "定期通院",
                },
            ]
        )
        assert result["status"] == "ok"
        assert result["registered_count"] == 3
        assert result["error_count"] == 0
        assert result["total_accompanied_visits"] == 3

    def test_import_invalid_staff(self, kimachiya_staff):
        """存在しないスタッフ名でエラーが返ること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = import_accompanied_visits(
            visits=[{
                "client_name": "山田健太",
                "staff_name": "存在しないスタッフ",
                "day": 15,
                "visit_type": "定期通院",
            }]
        )
        assert result["status"] == "ok"
        assert result["registered_count"] == 0
        assert result["error_count"] == 1
        assert "登録されていません" in result["errors"][0]

    def test_import_invalid_day(self, kimachiya_staff):
        """範囲外の日付でエラーが返ること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = import_accompanied_visits(
            visits=[{
                "client_name": "山田健太",
                "staff_name": "川崎聡",
                "day": 32,
                "visit_type": "定期通院",
            }]
        )
        assert result["status"] == "ok"
        assert result["registered_count"] == 0
        assert result["error_count"] == 1
        assert "範囲外" in result["errors"][0]

    def test_import_mixed_valid_invalid(self, kimachiya_staff):
        """有効・無効が混在する場合の部分登録。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = import_accompanied_visits(
            visits=[
                {
                    "client_name": "山田健太",
                    "staff_name": "川崎聡",
                    "day": 10,
                    "visit_type": "定期通院",
                },
                {
                    "client_name": "佐藤花子",
                    "staff_name": "存在しない人",
                    "day": 15,
                    "visit_type": "臨時通院",
                },
            ]
        )
        assert result["status"] == "ok"
        assert result["registered_count"] == 1
        assert result["error_count"] == 1

    def test_import_accumulates(self, kimachiya_staff):
        """複数回のインポートで蓄積されること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        import_accompanied_visits(
            visits=[{
                "client_name": "山田健太",
                "staff_name": "川崎聡",
                "day": 10,
                "visit_type": "定期通院",
            }]
        )
        result = import_accompanied_visits(
            visits=[{
                "client_name": "佐藤花子",
                "staff_name": "斎藤駿児",
                "day": 15,
                "visit_type": "臨時通院",
            }]
        )
        assert result["total_accompanied_visits"] == 2

    def test_import_empty_list(self, kimachiya_staff):
        """空リストで登録0件が返ること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = import_accompanied_visits(visits=[])
        assert result["status"] == "ok"
        assert result["registered_count"] == 0


# ===================================================================
# Tool 10: get_accompanied_visits
# ===================================================================
class TestGetAccompaniedVisits:
    def test_get_empty(self):
        """登録なしの場合、空リストが返ること。"""
        result = get_accompanied_visits()
        assert result["status"] == "ok"
        assert result["total_visits"] == 0
        assert result["visits"] == []

    def test_get_after_import(self, kimachiya_staff):
        """登録後に一覧が取得できること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        import_accompanied_visits(
            visits=[
                {
                    "client_name": "山田健太",
                    "staff_name": "川崎聡",
                    "day": 10,
                    "visit_type": "定期通院",
                    "hospital": "A病院",
                },
                {
                    "client_name": "佐藤花子",
                    "staff_name": "川崎聡",
                    "day": 20,
                    "visit_type": "臨時通院",
                },
            ]
        )
        result = get_accompanied_visits()
        assert result["status"] == "ok"
        assert result["total_visits"] == 2
        assert len(result["visits"]) == 2

    def test_get_by_staff_grouping(self, kimachiya_staff):
        """スタッフ別グループが正しいこと。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        import_accompanied_visits(
            visits=[
                {
                    "client_name": "山田健太",
                    "staff_name": "川崎聡",
                    "day": 10,
                    "visit_type": "定期通院",
                },
                {
                    "client_name": "佐藤花子",
                    "staff_name": "川崎聡",
                    "day": 20,
                    "visit_type": "臨時通院",
                },
                {
                    "client_name": "田中一郎",
                    "staff_name": "斎藤駿児",
                    "day": 15,
                    "visit_type": "定期通院",
                },
            ]
        )
        result = get_accompanied_visits()
        assert len(result["by_staff"]) == 2

        # Find kawasaki's entry
        kawasaki = next(
            s for s in result["by_staff"] if s["staff_name"] == "川崎聡"
        )
        assert kawasaki["visit_count"] == 2
        assert set(kawasaki["days"]) == {10, 20}

    def test_get_visit_has_required_fields(self, kimachiya_staff):
        """各visitに必須フィールドがあること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        import_accompanied_visits(
            visits=[{
                "client_name": "山田健太",
                "staff_name": "川崎聡",
                "day": 10,
                "visit_type": "定期通院",
                "hospital": "A病院",
                "note": "テスト",
            }]
        )
        result = get_accompanied_visits()
        visit = result["visits"][0]
        assert "staff" in visit
        assert "client" in visit
        assert "day" in visit
        assert "type" in visit
        assert "hospital" in visit
        assert "note" in visit


# ===================================================================
# Tool 11: analyze_schedule_balance
# ===================================================================
class TestAnalyzeScheduleBalance:
    def test_analyze_basic(self, kimachiya_template_path):
        """基本的なバランス分析が成功すること。"""
        result = analyze_schedule_balance(result_path=str(kimachiya_template_path))
        assert result["status"] == "ok"
        assert result["staff_count"] > 0
        assert result["total_days"] > 0

    def test_analyze_staff_detail(self, kimachiya_template_path):
        """スタッフ分析に必須フィールドがあること。"""
        result = analyze_schedule_balance(result_path=str(kimachiya_template_path))
        for staff in result["staff_analysis"]:
            assert "name" in staff
            assert "work_days" in staff
            assert "holidays" in staff
            assert "weekend_work" in staff
            assert "max_consecutive_work" in staff
            assert "max_consecutive_off" in staff
            assert "alerts" in staff

    def test_analyze_statistics(self, kimachiya_template_path):
        """全体統計値が含まれていること。"""
        result = analyze_schedule_balance(result_path=str(kimachiya_template_path))
        assert "average_work_days" in result
        assert "work_days_std" in result
        assert "average_weekend_work" in result
        assert "weekend_work_std" in result

    def test_analyze_nonexistent_file(self):
        """存在しないファイルでエラーが返ること。"""
        result = analyze_schedule_balance(result_path="/nonexistent/file.xlsx")
        assert result["status"] == "error"
        assert "見つかりません" in result["message"]

    def test_analyze_alerts_list(self, kimachiya_template_path):
        """alertsがリスト形式であること。"""
        result = analyze_schedule_balance(result_path=str(kimachiya_template_path))
        assert isinstance(result["alerts"], list)
        for staff in result["staff_analysis"]:
            assert isinstance(staff["alerts"], list)


# ===================================================================
# Tool 12: get_staffing_requirements
# ===================================================================
class TestGetStaffingRequirements:
    def test_b_type_default(self):
        """就労継続支援B型の基準が返されること。"""
        result = get_staffing_requirements()
        assert result["status"] == "ok"
        assert result["facility_type"] == "就労継続支援B型"
        assert result["user_count"] == 20
        assert len(result["standards"]) >= 3  # 職業指導員、サビ管、管理者

    def test_b_type_small_facility(self):
        """少人数施設の基準が正しいこと。"""
        result = get_staffing_requirements(user_count=10)
        staff_standard = result["standards"][0]
        assert staff_standard["required"] == 1  # 10人÷10 = 1人

    def test_b_type_large_facility(self):
        """大人数施設の基準が正しいこと。"""
        result = get_staffing_requirements(user_count=50)
        staff_standard = result["standards"][0]
        assert staff_standard["required"] == 5  # 50人÷10 = 5人

    def test_b_type_has_notes(self):
        """B型基準にnotesが含まれていること。"""
        result = get_staffing_requirements()
        assert len(result["notes"]) > 0

    def test_b_type_has_daily_minimum(self):
        """B型基準に日別最低人員があること。"""
        result = get_staffing_requirements()
        assert "daily_minimum" in result
        assert result["daily_minimum"] >= 2

    def test_a_type(self):
        """就労継続支援A型の基準が返されること。"""
        result = get_staffing_requirements(
            facility_type="就労継続支援A型", user_count=20
        )
        assert result["status"] == "ok"
        assert result["facility_type"] == "就労継続支援A型"

    def test_life_care(self):
        """生活介護の基準が返されること。"""
        result = get_staffing_requirements(
            facility_type="生活介護", user_count=20
        )
        assert result["status"] == "ok"
        assert result["facility_type"] == "生活介護"

    def test_unknown_facility_type(self):
        """不明な事業種別でもデフォルト基準が返ること。"""
        result = get_staffing_requirements(
            facility_type="不明な事業種別", user_count=20
        )
        assert result["status"] == "ok"
        assert len(result["standards"]) > 0

    def test_sabi_kan_standard(self):
        """サービス管理責任者の基準が含まれていること。"""
        result = get_staffing_requirements()
        roles = [s["role"] for s in result["standards"]]
        assert "サービス管理責任者" in roles

    def test_manager_standard(self):
        """管理者の基準が含まれていること。"""
        result = get_staffing_requirements()
        roles = [s["role"] for s in result["standards"]]
        assert "管理者" in roles


# ===================================================================
# Tool 13: transfer_staff
# ===================================================================
class TestTransferStaff:
    def test_transfer_without_facility(self):
        """事業所未設定でエラーが返ること。"""
        result = transfer_staff(action="add", staff_name="テスト太郎")
        assert result["status"] == "error"
        assert "事業所が未設定" in result["message"]

    def test_add_staff(self, kimachiya_staff):
        """新規スタッフの追加ができること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = transfer_staff(
            action="add",
            staff_name="新人花子",
            staff_info={
                "employee_type": "パート",
                "section": "ランチ",
                "vacation_days": 2,
                "holidays": 9,
            },
        )
        assert result["status"] == "ok"
        assert result["action"] == "add"
        assert result["new_total"] == 6

    def test_add_duplicate_staff(self, kimachiya_staff):
        """既存スタッフ名で追加するとエラーになること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = transfer_staff(action="add", staff_name="川崎聡")
        assert result["status"] == "error"
        assert "すでに登録" in result["message"]

    def test_remove_staff(self, kimachiya_staff):
        """スタッフの削除ができること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = transfer_staff(action="remove", staff_name="橋本由紀")
        assert result["status"] == "ok"
        assert result["action"] == "remove"
        assert result["new_total"] == 4

    def test_remove_nonexistent_staff(self, kimachiya_staff):
        """存在しないスタッフの削除でエラーが返ること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = transfer_staff(action="remove", staff_name="存在しない人")
        assert result["status"] == "error"
        assert "見つかりません" in result["message"]

    def test_remove_staff_with_visits(self, kimachiya_staff):
        """通院同行が紐づくスタッフの削除で警告が出ること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        import_accompanied_visits(
            visits=[{
                "client_name": "山田健太",
                "staff_name": "川崎聡",
                "day": 10,
                "visit_type": "定期通院",
            }]
        )
        result = transfer_staff(action="remove", staff_name="川崎聡")
        assert result["status"] == "ok"
        assert result["affected_accompanied_visits"] == 1
        assert len(result["warnings"]) > 0

    def test_update_staff(self, kimachiya_staff):
        """スタッフ情報の更新ができること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = transfer_staff(
            action="update",
            staff_name="島村誠",
            staff_info={"section": "仕込み", "vacation_days": 2},
        )
        assert result["status"] == "ok"
        assert result["action"] == "update"
        assert len(result["changes"]) > 0

    def test_update_nonexistent_staff(self, kimachiya_staff):
        """存在しないスタッフの更新でエラーが返ること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = transfer_staff(
            action="update",
            staff_name="存在しない人",
            staff_info={"section": "ランチ"},
        )
        assert result["status"] == "error"

    def test_update_without_info(self, kimachiya_staff):
        """更新情報なしでエラーが返ること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = transfer_staff(
            action="update",
            staff_name="島村誠",
        )
        assert result["status"] == "error"
        assert "staff_info" in result["message"]

    def test_invalid_action(self, kimachiya_staff):
        """不正なアクションでエラーが返ること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = transfer_staff(action="invalid", staff_name="川崎聡")
        assert result["status"] == "error"
        assert "不正な操作" in result["message"]

    def test_add_updates_presets(self, kimachiya_staff):
        """追加時にemployee_presetsも更新されること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        transfer_staff(
            action="add",
            staff_name="新人太郎",
            staff_info={"employee_type": "正規", "section": "仕込み"},
        )
        presets = _facility_state["employee_presets"]
        preset_names = [p.name for p in presets]
        assert "新人太郎" in preset_names

    def test_remove_updates_presets(self, kimachiya_staff):
        """削除時にemployee_presetsも更新されること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        transfer_staff(action="remove", staff_name="橋本由紀")
        presets = _facility_state["employee_presets"]
        preset_names = [p.name for p in presets]
        assert "橋本由紀" not in preset_names


# ===================================================================
# Tool 14: generate_shift_report
# ===================================================================
class TestGenerateShiftReport:
    def test_nonexistent_file(self):
        """存在しないファイルでエラーを返すこと。"""
        result = generate_shift_report(result_path="/tmp/nonexistent.xlsx")
        assert result["status"] == "error"
        assert "見つかりません" in result["message"]

    def test_basic_report(self, kimachiya_template_path):
        """基本的なレポート生成が成功すること。"""
        result = generate_shift_report(result_path=str(kimachiya_template_path))
        assert result["status"] == "ok"
        assert "report" in result

    def test_report_has_summary(self, kimachiya_template_path):
        """レポートにsummaryセクションがあること。"""
        result = generate_shift_report(result_path=str(kimachiya_template_path))
        report = result["report"]
        assert "summary" in report
        summary = report["summary"]
        assert "staff_count" in summary
        assert "total_days" in summary
        assert "overall_score" in summary
        assert "grade" in summary

    def test_report_has_balance(self, kimachiya_template_path):
        """レポートにbalanceセクションがあること。"""
        result = generate_shift_report(result_path=str(kimachiya_template_path))
        report = result["report"]
        assert "balance" in report
        balance = report["balance"]
        assert "average_work_days" in balance
        assert "staff_analysis" in balance

    def test_report_has_compliance(self, kimachiya_template_path):
        """レポートにcomplianceセクションがあること。"""
        result = generate_shift_report(result_path=str(kimachiya_template_path))
        report = result["report"]
        assert "compliance" in report
        compliance = report["compliance"]
        assert "is_compliant" in compliance

    def test_report_has_issues_and_recommendations(self, kimachiya_template_path):
        """レポートにissuesとrecommendationsがあること。"""
        result = generate_shift_report(result_path=str(kimachiya_template_path))
        report = result["report"]
        assert "issues" in report
        assert "recommendations" in report
        assert isinstance(report["issues"], list)
        assert isinstance(report["recommendations"], list)
        # recommendations は最低1つある（「良好です」を含む可能性がある）
        assert len(report["recommendations"]) >= 1

    def test_report_score_range(self, kimachiya_template_path):
        """スコアが0〜100の範囲であること。"""
        result = generate_shift_report(result_path=str(kimachiya_template_path))
        score = result["report"]["summary"]["overall_score"]
        assert 0 <= score <= 100

    def test_report_grade_is_valid(self, kimachiya_template_path):
        """グレードがA〜Dのいずれかであること。"""
        result = generate_shift_report(result_path=str(kimachiya_template_path))
        grade = result["report"]["summary"]["grade"]
        assert grade[0] in ("A", "B", "C", "D")

    def test_report_staff_detail(self, kimachiya_template_path):
        """レポートにstaff_detailがあること。"""
        result = generate_shift_report(result_path=str(kimachiya_template_path))
        report = result["report"]
        assert "staff_detail" in report
        assert isinstance(report["staff_detail"], list)


# ===================================================================
# Tool 15: simulate_scenario
# ===================================================================
class TestSimulateScenario:
    def test_nonexistent_file(self):
        """存在しないファイルでエラーを返すこと。"""
        result = simulate_scenario(
            base_template_path="/tmp/nonexistent.xlsx",
            scenario_type="remove_staff",
        )
        assert result["status"] == "error"
        assert "見つかりません" in result["message"]

    def test_invalid_scenario_type(self, kimachiya_template_path):
        """不明なシナリオ種別でエラーを返すこと。"""
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="invalid_type",
        )
        assert result["status"] == "error"
        assert "不明なシナリオ種別" in result["message"]

    def test_remove_staff_basic(self, kimachiya_template_path, kimachiya_staff):
        """スタッフ退職シミュレーションが成功すること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="remove_staff",
            scenario_params={"staff_name": "川崎聡"},
        )
        assert result["status"] == "ok"
        assert result["scenario"]["scenario_type"] == "remove_staff"
        assert result["scenario"]["staff_name"] == "川崎聡"
        assert result["scenario"]["staff_found"] is True

    def test_remove_staff_not_found(self, kimachiya_template_path, kimachiya_staff):
        """存在しないスタッフの退職シミュレーション。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="remove_staff",
            scenario_params={"staff_name": "存在しない人"},
        )
        assert result["status"] == "ok"
        assert result["scenario"]["staff_found"] is False

    def test_remove_staff_missing_name(self, kimachiya_template_path):
        """staff_nameなしでエラーを返すこと。"""
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="remove_staff",
            scenario_params={},
        )
        assert result["status"] == "error"
        assert "staff_name" in result["message"]

    def test_remove_staff_has_risk_level(self, kimachiya_template_path, kimachiya_staff):
        """退職シミュレーションにリスクレベルが含まれること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="remove_staff",
            scenario_params={"staff_name": "川崎聡"},
        )
        assert "risk_level" in result["scenario"]
        assert result["scenario"]["risk_level"] in ("高", "中", "低")

    def test_remove_staff_has_baseline(self, kimachiya_template_path, kimachiya_staff):
        """退職シミュレーションにbaseline情報が含まれること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="remove_staff",
            scenario_params={"staff_name": "川崎聡"},
        )
        assert "baseline" in result
        assert "staff_count" in result["baseline"]

    def test_add_staff_basic(self, kimachiya_template_path, kimachiya_staff):
        """スタッフ追加シミュレーションが成功すること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="add_staff",
            scenario_params={
                "staff_name": "新人太郎",
                "employee_type": "パート",
                "section": "ランチ",
            },
        )
        assert result["status"] == "ok"
        assert result["scenario"]["scenario_type"] == "add_staff"
        assert result["scenario"]["new_staff_count"] == 6

    def test_add_staff_has_buffer(self, kimachiya_template_path, kimachiya_staff):
        """追加シミュレーションにstaffing_bufferが含まれること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="add_staff",
            scenario_params={"staff_name": "新人"},
        )
        assert "staffing_buffer" in result["scenario"]

    def test_change_users_basic(self, kimachiya_template_path, kimachiya_staff):
        """利用者数変更シミュレーションが成功すること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="change_users",
            scenario_params={"new_user_count": 30},
        )
        assert result["status"] == "ok"
        assert result["scenario"]["scenario_type"] == "change_users"
        assert result["scenario"]["new_user_count"] == 30

    def test_change_users_has_gap(self, kimachiya_template_path, kimachiya_staff):
        """利用者数変更シミュレーションにstaff_gapが含まれること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="change_users",
            scenario_params={"new_user_count": 30},
        )
        assert "staff_gap" in result["scenario"]
        assert "meets_new_minimum" in result["scenario"]

    def test_change_constraint_basic(self, kimachiya_template_path):
        """制約変更シミュレーションが成功すること。"""
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="change_constraint",
            scenario_params={"constraint_type": "kitchen_min_workers"},
        )
        assert result["status"] == "ok"
        assert result["scenario"]["scenario_type"] == "change_constraint"

    def test_change_constraint_invalid(self, kimachiya_template_path):
        """存在しない制約でエラーを返すこと。"""
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="change_constraint",
            scenario_params={"constraint_type": "nonexistent_constraint"},
        )
        assert result["status"] == "error"
        assert "存在しません" in result["message"]

    def test_change_constraint_missing_type(self, kimachiya_template_path):
        """constraint_typeなしでエラーを返すこと。"""
        result = simulate_scenario(
            base_template_path=str(kimachiya_template_path),
            scenario_type="change_constraint",
            scenario_params={},
        )
        assert result["status"] == "error"
        assert "constraint_type" in result["message"]

    def test_all_scenarios_have_recommendations(self, kimachiya_template_path, kimachiya_staff):
        """全シナリオタイプにrecommendationsが含まれること。"""
        setup_facility(name="木町家", staff=kimachiya_staff)

        scenarios = [
            ("remove_staff", {"staff_name": "川崎聡"}),
            ("add_staff", {"staff_name": "新人"}),
            ("change_users", {"new_user_count": 25}),
            ("change_constraint", {"constraint_type": "kitchen_min_workers"}),
        ]

        for scenario_type, params in scenarios:
            result = simulate_scenario(
                base_template_path=str(kimachiya_template_path),
                scenario_type=scenario_type,
                scenario_params=params,
            )
            assert result["status"] == "ok", f"{scenario_type} failed"
            assert "recommendations" in result, f"{scenario_type} has no recommendations"
            assert isinstance(result["recommendations"], list)
