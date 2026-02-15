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
    """Execute one pipeline stage, return (stdout, stderr, time_ms, exit_code)."""
    t0 = time.perf_counter()
    p = subprocess.run(cmd, shell=True, input=input_data,
                       capture_output=True, text=True, timeout=30)
    return p.stdout, p.stderr, round((time.perf_counter() - t0) * 1000, 2), p.returncode


def inspect_pipeline(command, stdin_data=""):
    """Run each stage of a pipeline and collect per-stage stats."""
    stages = parse_pipeline(command)
    results, data = [], stdin_data
    for i, cmd in enumerate(stages):
        in_l = count_lines(data)
        out, stderr, ms, code = run_stage(cmd, data)
        out_l = count_lines(out)
        preview = [l for l in out.split("\n") if l][:3]
        results.append(dict(
            stage=i + 1, cmd=cmd, in_lines=in_l, out_lines=out_l,
            in_bytes=len(data.encode()), out_bytes=len(out.encode()),
            time_ms=ms, exit_code=code, delta=out_l - in_l,
            preview=preview, stdout=out, stderr=stderr,
        ))
        data = out
    return results


def format_report(results, color=True):
    """Format results into a human-readable report."""
    B = "\033[1m" if color else ""
    R = "\033[0m" if color else ""
    G = "\033[32m" if color else ""
    Y = "\033[33m" if color else ""
    C = "\033[36m" if color else ""

    lines = []
    sep = "\u2550" * 58
    lines.append(f"{B}{sep}{R}")
    lines.append(f"{B}  PipeScope \u2014 Pipeline Debug Report{R}")
    lines.append(f"{B}{sep}{R}")
    lines.append("")

    total_ms = 0
    for r in results:
        total_ms += r["time_ms"]
        delta_str = f"+{r['delta']}" if r["delta"] > 0 else str(r["delta"])
        color_d = G if r["delta"] > 0 else (Y if r["delta"] < 0 else C)
        lines.append(f"{B}Stage {r['stage']}: {r['cmd']}{R}")
        lines.append(f"  Lines: {r['in_lines']} \u2192 {r['out_lines']} ({color_d}{delta_str} lines{R})")
        lines.append(f"  Bytes: {r['in_bytes']} \u2192 {r['out_bytes']}  |  Time: {r['time_ms']}ms  |  Exit: {r['exit_code']}")
        if r["preview"]:
            lines.append("  Preview:")
            for pl in r["preview"]:
                lines.append(f"    \u2502 {pl}")
        lines.append("")

    if results:
        first_in = results[0]["in_lines"]
        last_out = results[-1]["out_lines"]
        pct = round(last_out / first_in * 100) if first_in else 0
        lines.append(f"{B}Summary: {len(results)} stages | {round(total_ms, 1)}ms total | {first_in}\u2192{last_out} lines ({pct}% retention){R}")

    return "\n".join(lines)


def format_json(results, command):
    """Format results as a JSON object for machine consumption."""
    stages = []
    for r in results:
        stages.append({
            "index": r["stage"] - 1,
            "command": r["cmd"],
            "stdout": r["stdout"],
            "stderr": r["stderr"],
            "exit_code": r["exit_code"],
            "line_count": r["out_lines"],
            "byte_count": r["out_bytes"],
        })
    return json.dumps({"pipeline": command, "stages": stages}, ensure_ascii=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description="PipeScope \u2014 Shell pipeline debugger")
    ap.add_argument("command", help="Pipeline command string")
    ap.add_argument("--no-color", action="store_true", help="Disable colored output")
    ap.add_argument("--output-format", choices=["text", "json"], default="text",
                    help="Output format: text (default) or json")
    ap.add_argument("--output-file", type=str, default=None,
                    help="Write output to file instead of stdout")
    args = ap.parse_args(argv)

    stdin_data = ""
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()

    results = inspect_pipeline(args.command, stdin_data)

    if args.output_format == "json":
        output = format_json(results, args.command)
    else:
        output = format_report(results, color=not args.no_color)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(output + "\n")
    else:
        print(output)


if __name__ == "__main__":
    main()
