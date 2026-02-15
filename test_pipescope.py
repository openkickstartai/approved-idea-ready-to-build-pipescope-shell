"""Tests for PipeScope pipeline debugger."""
from pipescope import parse_pipeline, count_lines, inspect_pipeline, format_report


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
    assert "67%" in report


def test_inspect_with_stdin_data():
    results = inspect_pipeline("grep x", stdin_data="ax\nby\ncx\n")
    assert len(results) == 1
    assert results[0]["in_lines"] == 3
    assert results[0]["out_lines"] == 2
    assert results[0]["delta"] == -1
