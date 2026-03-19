from botbook.runtime.memory import history

def show_logs():

    runs = history()

    for r in runs:
        print("\nAgent:", r["agent"])
        print("Task:", r["task"])
        print("Time:", r["time"])
