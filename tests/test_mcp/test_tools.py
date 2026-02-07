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
    check_compliance as _check_compliance_tool,
    explain_result as _explain_result_tool,
    generate_shift_template as _generate_shift_template_tool,
    list_constraints as _list_constraints_tool,
    run_optimization as _run_optimization_tool,
    setup_facility as _setup_facility_tool,
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
