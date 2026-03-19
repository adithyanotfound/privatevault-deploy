import os
import json

RUN_DIR="runs"

def list_runs():

    if not os.path.exists(RUN_DIR):
        print("No runs")
        return

    for f in os.listdir(RUN_DIR):

        with open(f"{RUN_DIR}/{f}") as file:
            data=json.load(file)

        print(
            data["run_id"],
            data["agent"],
            data["status"]
        )
