import sys
from lork.devtools import list_runs, inspect_run, replay_run, trace_run, graph_run, stats_run

def main():
    if len(sys.argv) < 2:
        print("Commands:")
        print("  lork runs")
        print("  lork inspect <run_id>")
        print("  lork replay <run_id>")
        print("  lork trace <run_id>")
        print("  lork graph <run_id>")
        print("  lork stats <run_id>")
        return

    cmd = sys.argv[1]

    if cmd == "runs":
        list_runs()
    elif cmd == "inspect":
        inspect_run(sys.argv[2])
    elif cmd == "replay":
        replay_run(sys.argv[2])
    elif cmd == "trace":
        trace_run(sys.argv[2])
    elif cmd == "graph":
        graph_run(sys.argv[2])
    elif cmd == "stats":
        stats_run(sys.argv[2])
    else:
        print("Unknown command:", cmd)
