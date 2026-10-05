#!/bin/sh
# One command per host: run a benchmark suite (backend/benchmarks/suites/)
# start to finish, results in backend/benchmark-results/<host>/.
#   ./bench.sh full --host m4-dd16      run the "full" suite on this machine
#   ./bench.sh list                     the suites and their runs
#   ./bench.sh random --host m4-dd16 --resume
# See docs/benchmarks/README.md. Needs Docker and Python 3.11+ (stdlib only).
cd "$(dirname "$0")" || exit 1
for py in python3.13 python3.12 python3.11 python3; do
  if command -v "$py" >/dev/null 2>&1 &&
    "$py" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    case "$1" in
      list | summarize | run | -h | --help) exec "$py" backend/scripts/bench_suite.py "$@" ;;
      *) exec "$py" backend/scripts/bench_suite.py run "$@" ;;
    esac
  fi
done
echo "bench.sh needs Python 3.11 or newer (python3.11+ on PATH)" >&2
exit 1
