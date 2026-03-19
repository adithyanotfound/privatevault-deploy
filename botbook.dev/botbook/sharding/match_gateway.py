import asyncio

class MatchGateway:

    def __init__(self, registry):
        self.registry = registry

    async def match(self, intent):

        tasks = []

        for shard_id in self.registry.shards:
            shard = self.registry.shards[shard_id]

            async def search(s=shard):
                members = s.list()
                return [m for m in members if set(intent.required_capabilities).intersection(set(m.capabilities))]

            tasks.append(search())

        results = await asyncio.gather(*tasks)

        flat = [m for sub in results for m in sub]

        flat.sort(key=lambda m: m.trust_score, reverse=True)

        return flat[:intent.max_results]
