from .router import ShardRouter
from .member_shard import MemberShard

class ShardedRegistry:

    def __init__(self, shard_count=64):
        self.router = ShardRouter(shard_count)
        self.shards = {i: MemberShard(i) for i in range(shard_count)}

    def save(self, member):

        shard_id = self.router.shard_for(member.member_id)
        self.shards[shard_id].save(member)

    def get(self, member_id):

        shard_id = self.router.shard_for(member_id)
        return self.shards[shard_id].get(member_id)

    def list_shard(self, shard_id):
        return self.shards[shard_id].list()
