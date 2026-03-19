
class RunsAPI:

    def __init__(self, replay_engine):
        self.replay_engine = replay_engine

    async def replay(self, run_id: str):
        return await self.replay_engine.replay(run_id)

    async def fork(self, run_id: str, new_run_id: str):
        return await self.replay_engine.fork(run_id, new_run_id)

class RunDebugger:

    def __init__(self, debugger):
        self.debugger = debugger

    async def inspect(self, run_id: str):
        return await self.debugger.inspect(run_id)

    async def replay(self, run_id: str):
        return await self.debugger.replay(run_id)

    async def fork(self, run_id: str, step: int, new_run_id: str):
        return await self.debugger.fork(run_id, step, new_run_id)
