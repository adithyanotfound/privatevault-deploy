class MemberShard:

    def __init__(self, shard_id):
        self.shard_id = shard_id
        self.members = {}

    def save(self, member):
        self.members[member.member_id] = member

    def get(self, member_id):
        return self.members.get(member_id)

    def list(self):
        return list(self.members.values())
