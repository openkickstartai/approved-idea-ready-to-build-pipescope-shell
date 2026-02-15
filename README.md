# PipeScope 🔬

**Shell pipeline stage-by-stage debugger** — see how data flows, shrinks, and transforms through each pipe stage.

## Problem

Ever built a long shell pipeline and wondered where your data disappeared?

```bash
cat access.log | grep ERROR | awk '{print $4}' | sort | uniq -c | sort -rn | head
# Output is empty... but which stage lost the data?
```

## Solution

PipeScope executes each stage independently and shows you exactly what happens at every step.

## Install

```bash
pip install -e .
# or run directly:
python pipescope.py "your | pipeline | here"
```

## Usage

```bash
# Basic usage
pipescope "printf 'foo\nbar\nbaz\n' | grep b | sort"

# JSON output for scripting
pipescope --json "ls | grep py | wc -l"

# Pipe data in from a file
cat data.txt | pipescope "grep ERROR | cut -d' ' -f3 | sort -u"

# Disable colors
pipescope --no-color "echo hello | cat"
```

## Output Example

```
════════════════════════════════════════════════════════════
  PipeScope — Pipeline Debug Report
════════════════════════════════════════════════════════════

Stage 1: printf 'alpha\nbeta\ngamma\n'
  Lines: 0 → 3 (+3 lines)
  Bytes: 0 → 18  |  Time: 3.2ms  |  Exit: 0
  Preview:
    │ alpha
    │ beta
    │ gamma

Stage 2: grep a
  Lines: 3 → 2 (-1 lines)
  Bytes: 18 → 12  |  Time: 2.1ms  |  Exit: 0
  Preview:
    │ alpha
    │ gamma

Summary: 2 stages | 5.3ms total | 3→2 lines (67% retention)
```

## Development

```bash
pip install -r requirements.txt
pytest test_pipescope.py -v
```

## License

MIT
