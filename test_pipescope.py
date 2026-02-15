"""Tests for PipeScope pipeline debugger."""
import json
import os
import tempfile
from pipescope import parse_pipeline, count_lines, inspect_pipeline, format_report, format_json, main


def test_parse_simple_pipeline():
    result = parse_pipeline("cat foo | grep bar | wc -l")
    assert result == ["cat foo", "grep bar", "wc -l"]


def test_parse_single_quoted_pipe():
    result = parse_pipeline("echo 'a|b' | grep a")
    assert result == ["echo 'a|b'", "grep a"]


def test_parse_double_quoted_pipe():
    result = parse_pipeline('echo "x|y" | cat')
    assert result == ['echo "x|y"', "cat"]


def test_count_lines_empty():
    assert count_lines("") == 0


def test_count_lines_trailing_newline():
    assert count_lines("a\nb\nc\n") == 3


def test_count_lines_no_trailing_newline():
    assert count_lines("hello") == 1


def test_inspect_single_stage():
    results = inspect_pipeline("printf 'hello\\n'")
    assert len(results) == 1
    assert results[0]["out_lines"] == 1
    assert results[0]["exit_code"] == 0
    assert results[0]["preview"] == ["hello"]


def test_inspect_filter_pipeline():
    results = inspect_pipeline("printf 'alpha\\nbeta\\ngamma\\n' | grep a")
    assert len(results) == 2
    assert results[0]["out_lines"] == 3
    assert results[1]["out_lines"] == 2
    assert results[1]["delta"] == -1


def test_inspect_passthrough():
    results = inspect_pipeline("printf 'x\\ny\\n' | cat | cat")
    assert len(results) == 3
    for r in results[1:]:
        assert r["delta"] == 0
    assert results[-1]["out_lines"] == 2


def test_format_report_structure():
    results = inspect_pipeline("printf 'test\\n'")
    report = format_report(results, color=False)
    assert "Stage 1" in report
    assert "printf" in report
    assert "Summary" in report


def test_format_report_retention():
    results = inspect_pipeline("printf 'a\\nb\\nc\\n' | grep a")
    report = format_report(results, color=False)
    assert "retention" in report


# === JSON output tests ===

def test_json_output_valid_structure():
    """JSON output is valid and contains required top-level keys with correct types."""
    command = "echo hello | tr h H"
    results = inspect_pipeline(command)
    output = format_json(results, command)
    data = json.loads(output)
    assert "pipeline" in data
    assert "stages" in data
    assert isinstance(data["pipeline"], str)
    assert isinstance(data["stages"], list)
    assert data["pipeline"] == command
    assert len(data["stages"]) == 2


def test_json_output_field_types():
    """Each stage in JSON output has all required fields with correct types."""
    command = "printf 'foo\\nbar\\n' | grep foo"
    results = inspect_pipeline(command)
    output = format_json(results, command)
    data = json.loads(output)
    assert len(data["stages"]) == 2
    required_fields = {
        "index": int, "command": str, "stdout": str,
        "stderr": str, "exit_code": int, "line_count": int, "byte_count": int,
    }
    for stage in data["stages"]:
        for field, ftype in required_fields.items():
            assert field in stage, f"Missing field: {field}"
            assert isinstance(stage[field], ftype), f"{field} should be {ftype.__name__}"


def test_json_output_content_correctness():
    """JSON content reflects actual pipeline execution: stdout, line_count, exit_code."""
    command = "printf 'hello\\nworld\\n' | grep hello"
    results = inspect_pipeline(command)
    output = format_json(results, command)
    data = json.loads(output)
    stage0 = data["stages"][0]
    assert stage0["index"] == 0
    assert "hello" in stage0["stdout"]
    assert "world" in stage0["stdout"]
    assert stage0["exit_code"] == 0
    assert stage0["line_count"] == 2
    assert stage0["byte_count"] > 0
    stage1 = data["stages"][1]
    assert stage1["index"] == 1
    assert stage1["command"] == "grep hello"
    assert "hello" in stage1["stdout"]
    assert "world" not in stage1["stdout"]
    assert stage1["line_count"] == 1
    assert stage1["exit_code"] == 0
