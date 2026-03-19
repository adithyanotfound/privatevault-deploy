import os

NODE_ID = os.getenv("BOTBOOK_NODE_ID","node-1")
TOTAL_NODES = int(os.getenv("BOTBOOK_CLUSTER_SIZE","4"))

def owns_shard(shard_id):
    return shard_id % TOTAL_NODES == int(NODE_ID.split("-")[-1])
