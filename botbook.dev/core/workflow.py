class WorkflowEngine:

    def run(self, agents, task):

        chain = []

        for i in range(len(agents) - 1):
            chain.append({
                "from": agents[i],
                "to": agents[i+1],
                "task": task
            })

        return {
            "workflow": chain
        }

workflow_engine = WorkflowEngine()
