#!/usr/bin/env python3
"""PipeScope - Shell pipeline stage-by-stage debugger."""
import argparse, difflib, json, subprocess, sys, time


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
            preview=preview, output=out
        ))
        data = out
    return results


def format_report(results, color=True):
    """Format results into a human-readable report."""
    if color:
        BOLD, GREEN, RED, CYAN, RESET = (
            "\033[1m", "\033[32m", "\033[31m", "\033[36m", "\033[0m")
    else:
        BOLD = GREEN = RED = CYAN = RESET = ""
    lines = []
    lines.append(f"{BOLD}{'\u2550' * 58}{RESET}")
    lines.append(f"{BOLD}  PipeScope \u2014 Pipeline Debug Report{RESET}")
    lines.append(f"{BOLD}{'\u2550' * 58}{RESET}")
    lines.append("")
    total_ms = 0
    for r in results:
        total_ms += r["time_ms"]
        delta_str = f"+{r['delta']}" if r['delta'] >= 0 else str(r['delta'])
        color_d = GREEN if r['delta'] > 0 else RED if r['delta'] < 0 else CYAN
        lines.append(f"{BOLD}Stage {r['stage']}: {r['cmd']}{RESET}")
        lines.append(
            f"  Lines: {r['in_lines']} \u2192 {r['out_lines']} "
            f"({color_d}{delta_str} lines{RESET})")
        lines.append(
            f"  Bytes: {r['in_bytes']} \u2192 {r['out_bytes']}  |  "
            f"Time: {r['time_ms']}ms  |  Exit: {r['exit_code']}")
        if r['preview']:
            lines.append("  Preview:")
            for pl in r['preview']:
                lines.append(f"    \u2502 {pl}")
        lines.append("")
    first = results[0]["in_lines"] if results else 0
    last = results[-1]["out_lines"] if results else 0
    pct = round(last / first * 100) if first > 0 else 0
    lines.append(
        f"{BOLD}Summary: {len(results)} stages | {round(total_ms, 1)}ms total "
        f"| {first}\u2192{last} lines ({pct}% retention){RESET}")
    return "\n".join(lines)


def format_diff(results, color=True):
    """Format unified diffs between consecutive pipeline stages."""
    if color:
        GREEN, RED, YELLOW, RESET = (
            "\033[32m", "\033[31m", "\033[33m", "\033[0m")
    else:
        GREEN = RED = YELLOW = RESET = ""
    lines = []
    for i, r in enumerate(results):
        if not r["output"]:
            lines.append(
                f"[stage {r['stage']}] \u26a0 No output \u2014 "
                f"all data filtered out")
            continue
        if i == 0:
            continue
        prev_output = results[i - 1]["output"]
        curr_output = r["output"]
        prev_lines = prev_output.splitlines()
        curr_lines = curr_output.splitlines()
        diff = list(difflib.unified_diff(
            prev_lines, curr_lines,
            fromfile=f"stage {i}", tofile=f"stage {i + 1}",
            lineterm=""))
        if diff:
            for d in diff:
                if d.startswith("+++") or d.startswith("---"):
                    lines.append(f"{YELLOW}{d}{RESET}")
                elif d.startswith("@@"):
                    lines.append(f"{YELLOW}{d}{RESET}")
                elif d.startswith("+"):
                    lines.append(f"{GREEN}{d}{RESET}")
                elif d.startswith("-"):
                    lines.append(f"{RED}{d}{RESET}")
                else:
                    lines.append(d)
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="PipeScope - Shell pipeline debugger")
    parser.add_argument("command", help="Pipeline command string")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    parser.add_argument("--diff", action="store_true",
                        help="Show colored diffs between stages")
    args = parser.parse_args()
    stdin_data = ""
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()
    results = inspect_pipeline(args.command, stdin_data)
    use_color = not args.no_color
    if args.json:
        safe = [{k: v for k, v in r.items() if k != "output"}
                for r in results]
        print(json.dumps(safe, indent=2))
    else:
        print(format_report(results, color=use_color))
        if args.diff:
            diff_out = format_diff(results, color=use_color)
            if diff_out:
                print()
                print(diff_out)


if __name__ == "__main__":
    main()
