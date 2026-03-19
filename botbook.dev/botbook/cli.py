import subprocess
import sys

from botbook.agent_scaffold import create_agent
from botbook.runtime.executor import run as run_agent
from botbook.runtime.workflow import run_workflow
from botbook.runtime.memory import history
from botbook.runtime.project import init_project
from botbook.runtime.inspect import inspect_run
from botbook.runtime.logs import show_logs
from botbook.runtime.deploy import deploy

VERSION="0.1.0"

def start():
    subprocess.run(
        ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]
    )

def init():
    init_project()

def make():
    create_agent(sys.argv[2])

def run():
    agent=sys.argv[2]
    task=" ".join(sys.argv[3:])
    run_agent(agent,task)

def workflow():
    file=sys.argv[2]
    task=" ".join(sys.argv[3:])
    run_workflow(file,task)

def runs():
    for r in history():
        print(r)

def inspect():
    inspect_run()

def logs():
    show_logs()

def help():

    print("""

BotBook CLI

Lifecycle

botbook init
botbook make <agent>
botbook run <agent> "<task>"

Orchestration

botbook workflow <pipeline.yaml> "<task>"

Observability

botbook inspect
botbook logs

Deployment

botbook deploy

""")

def main():

    if len(sys.argv)<2:
        help()
        return

    cmd=sys.argv[1]

    if cmd=="init":
        init()

    elif cmd=="make":
        make()

    elif cmd=="run":
        run()

    elif cmd=="workflow":
        workflow()

    elif cmd=="inspect":
        inspect()

    elif cmd=="logs":
        logs()

    elif cmd=="deploy":
        deploy()

    else:
        help()

if __name__=="__main__":
    main()
