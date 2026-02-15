#!/usr/bin/env python3
"""PipeScope - Shell pipeline stage-by-stage debugger."""
import argparse, json, subprocess, sys, time


def parse_pipeline(cmd):
    """Split a pipeline command by | while respecting quotes."""
    stages, buf, sq, dq = [], [], False, False
    for c in cmd:
        if c == "'" and not dq:
            sq = not sq
        elif c == '"' and not sq:
            dq = not dq
        elif c == "|" and not sq and not dq:
            stages.append("".join(buf).strip())
            buf = []
            continue
        buf.append(c)
    if buf:
        stages.append("".join(buf).strip())
    return [s for s in stages if s]


def count_lines(data):
    """Count lines in text data, handling trailing newlines."""
    if not data:
        return 0
    lines = data.split("\n")
    return len(lines) - (1 if lines[-1] == "" else 0)


def run_stage(cmd, input_data):
    """Execute one pipeline stage, return (stdout, time_ms, exit_code)."""
    t0 = time.perf_counter()
    p = subprocess.run(cmd, shell=True, input=input_data,
                       capture_output=True, text=True, timeout=30)
    return p.stdout, round((time.perf_counter() - t0) * 1000, 2), p.returncode


def inspect_pipeline(command, stdin_data=""):
    """Run each stage of a pipeline and collect per-stage stats."""
    stages = parse_pipeline(command)
    results, data = [], stdin_data
    for i, cmd in enumerate(stages):
        in_l = count_lines(data)
        out, ms, code = run_stage(cmd, data)
        out_l = count_lines(out)
        preview = [l for l in out.split("\n") if l][:3]
        results.append(dict(
            stage=i + 1, cmd=cmd, in_lines=in_l, out_lines=out_l,
            in_bytes=len(data.encode()), out_bytes=len(out.encode()),
            time_ms=ms, exit_code=code, delta=out_l - in_l,
            preview=preview,
        ))
        data = out
    return results


def format_bytes(n):
    """Format byte count for human-readable display."""
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.0f}MB"
    elif n >= 1024:
        return f"{n / 1024:.0f}KB"
    else:
        return f"{n}B"


def format_report(results, color=True):
    """Format the standard debug report."""
    sep = "\u2550" * 58
    lines = [sep, "  PipeScope \u2014 Pipeline Debug Report", sep, ""]
    for r in results:
        d = r["delta"]
        sign = "+" if d >= 0 else ""
        lines.append(f"Stage {r['stage']}: {r['cmd']}")
        lines.append(f"  Lines: {r['in_lines']} \u2192 {r['out_lines']} ({sign}{d} lines)")
        lines.append(
            f"  Bytes: {r['in_bytes']} \u2192 {r['out_bytes']}  |  "
            f"Time: {r['time_ms']}ms  |  Exit: {r['exit_code']}"
        )
        if r["preview"]:
            lines.append("  Preview:")
            for p in r["preview"]:
                lines.append(f"    \u2502 {p}")
        lines.append("")
    total_ms = round(sum(r["time_ms"] for r in results), 2)
    first_out = results[0]["out_lines"] if results else 0
    last_out = results[-1]["out_lines"] if results else 0
    retention = round(last_out / first_out * 100) if first_out else 0
    lines.append(
        f"Summary: {len(results)} stages | {total_ms}ms total | "
        f"{first_out}\u2192{last_out} lines ({retention}% retention)"
    )
    return "\n".join(lines)


def format_stats_table(results):
    """Format a plain-text stats summary table with delta indicators."""
    cmd_width = max((len(r["cmd"]) for r in results), default=7)
    cmd_width = max(cmd_width, 7)
    lines_width = max((len(str(r["out_lines"])) for r in results), default=5)
    lines_width = max(lines_width, 5)
    bytes_strs = [format_bytes(r["out_bytes"]) for r in results]
    bytes_width = max((len(s) for s in bytes_strs), default=5)
    bytes_width = max(bytes_width, 5)
    time_strs = [str(r["time_ms"]) for r in results]
    time_width = max((len(s) for s in time_strs), default=8)
    time_width = max(time_width, 8)

    header = (
        f"{'Stage':<5} | {'Command':<{cmd_width}} | "
        f"{'Lines':<{lines_width}} | {'Bytes':<{bytes_width}} | "
        f"{'Time(ms)':<{time_width}} | Exit"
    )
    sep = "-" * len(header)
    rows = [header, sep]
    for i, r in enumerate(results):
        row = (
            f"{r['stage']:<5} | {r['cmd']:<{cmd_width}} | "
            f"{r['out_lines']:<{lines_width}} | {bytes_strs[i]:<{bytes_width}} | "
            f"{time_strs[i]:<{time_width}} | {r['exit_code']}"
        )
        rows.append(row)

    # Delta indicators between consecutive stages
    if len(results) > 1:
        rows.append("")
        for i in range(1, len(results)):
            prev_lines = results[i - 1]["out_lines"]
            curr_lines = results[i]["out_lines"]
            if prev_lines > 0:
                pct = (1 - curr_lines / prev_lines) * 100
                if pct > 0:
                    indicator = f"\u25bc{pct:.1f}%"
                elif pct < 0:
                    indicator = f"\u25b2{abs(pct):.1f}%"
                else:
                    indicator = "unchanged"
            elif curr_lines > 0:
                indicator = "\u25b2new"
            else:
                indicator = "unchanged"
            rows.append(f"Lines: {prev_lines} \u2192 {curr_lines} ({indicator})")

    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(
        description="PipeScope \u2014 Shell pipeline stage-by-stage debugger")
    parser.add_argument("command", help="Pipeline command (quoted)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colors")
    parser.add_argument("--stats", action="store_true",
                        help="Print per-stage statistics table")
    args = parser.parse_args()

    stdin_data = ""
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()

    results = inspect_pipeline(args.command, stdin_data)

    if args.json:
        print(json.dumps(results, indent=2))
    elif args.stats:
        print(format_stats_table(results))
    else:
        print(format_report(results, color=not args.no_color))


if __name__ == "__main__":
    main()
