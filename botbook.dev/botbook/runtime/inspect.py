from botbook.runtime.memory import history

def inspect_run():

    runs = history()

    if not runs:
        print("No runs found")
        return

    last = runs[-1]

    print("\nLast Run")
    print("--------")
    print("Agent:", last["agent"])
    print("Task:", last["task"])
    print("Result:\n")
    print(last["result"])
