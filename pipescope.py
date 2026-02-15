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
            time_ms=ms, exit_code=code, delta=out_l - in_l, preview=preview,
        ))
        data = out
    return results


def format_report(results, color=True):
    """Format inspection results into a human-readable report."""
    if color:
        B, G, R, C, D, X = "\033[1m", "\033[32m", "\033[31m", "\033[36m", "\033[2m", "\033[0m"
    else:
        B = G = R = C = D = X = ""
    out = [f"\n{B}{'═' * 60}{X}",
           f"{B}  PipeScope — Pipeline Debug Report{X}",
           f"{B}{'═' * 60}{X}"]
    for r in results:
        d = r["delta"]
        ds = f"{G}+{d}{X}" if d > 0 else (f"{R}{d}{X}" if d < 0 else "±0")
        out.append(f"\n{C}Stage {r['stage']}{X}: {B}{r['cmd']}{X}")
        out.append(f"  Lines: {r['in_lines']} → {r['out_lines']} ({ds} lines)")
        out.append(f"  Bytes: {r['in_bytes']} → {r['out_bytes']}  |  "
                   f"Time: {r['time_ms']}ms  |  Exit: {r['exit_code']}")
        if r["preview"]:
            out.append(f"  {D}Preview:{X}")
            for line in r["preview"]:
                out.append(f"    {D}│{X} {line}")
    if results:
        total = sum(r["time_ms"] for r in results)
        first, last = results[0]["out_lines"], results[-1]["out_lines"]
        pct = f"{last / first * 100:.0f}%" if first else "N/A"
        out.append(f"\n{B}Summary:{X} {len(results)} stages | {total:.1f}ms "
                   f"total | {first}→{last} lines ({pct} retention)\n")
    return "\n".join(out)


def main(argv=None):
    """CLI entry point."""
    ap = argparse.ArgumentParser(prog="pipescope",
                                 description="Shell pipeline debugger")
    ap.add_argument("pipeline", help="Pipeline command (quote the whole string)")
    ap.add_argument("-n", "--samples", type=int, default=3,
                    help="Preview lines per stage (default: 3)")
    ap.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    args = ap.parse_args(argv)
    stdin_data = ""
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()
    results = inspect_pipeline(args.pipeline, stdin_data)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results, color=not args.no_color))
    return results


if __name__ == "__main__":
    main()
