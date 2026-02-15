"""Tests for PipeScope pipeline debugger."""
from pipescope import (
    parse_pipeline, count_lines, inspect_pipeline,
    format_report, format_stats_table,
)


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


# --- Stats feature tests ---

def test_stats_line_counts():
    """Assert correct line counts across a multi-stage pipeline."""
    results = inspect_pipeline("seq 1 10 | head -5 | tail -3")
    assert results[0]["out_lines"] == 10
    assert results[1]["out_lines"] == 5
    assert results[2]["out_lines"] == 3


def test_stats_byte_counts():
    """Assert correct byte counts for known output."""
    results = inspect_pipeline("printf 'hello\\n'")
    # "hello\n" = 6 bytes, input is empty = 0 bytes
    assert results[0]["out_bytes"] == 6
    assert results[0]["in_bytes"] == 0


def test_stats_timing_non_negative():
    """Assert that all timing values are non-negative."""
    results = inspect_pipeline("seq 1 100 | head -10 | tail -5")
    for r in results:
        assert r["time_ms"] >= 0, (
            f"Stage {r['stage']} has negative time: {r['time_ms']}"
        )


def test_stats_table_format():
    """Assert stats table contains expected headers and data."""
    results = inspect_pipeline("seq 1 20 | head -10")
    table = format_stats_table(results)
    assert "Stage" in table
    assert "Command" in table
    assert "Lines" in table
    assert "Bytes" in table
    assert "Time(ms)" in table
    assert "Exit" in table
    assert "seq 1 20" in table
    assert "head -10" in table


def test_stats_delta_indicators():
    """Assert delta indicators are shown between stages."""
    results = inspect_pipeline("seq 1 100 | head -10")
    table = format_stats_table(results)
    # Should show Lines: 100 -> 10 with a down indicator
    assert "\u2192" in table
    assert "\u25bc" in table
