import hashlib

class ShardRouter:

    def __init__(self, shard_count=64):
        self.shard_count = shard_count

    def _hash(self, key: str) -> int:
        h = hashlib.sha256(key.encode()).hexdigest()
        return int(h, 16)

    def shard_for(self, member_id: str) -> int:
        return self._hash(member_id) % self.shard_count

    def node_for(self, member_id: str, nodes: list[str]) -> str:
        shard = self.shard_for(member_id)
        idx = shard % len(nodes)
        return nodes[idx]
