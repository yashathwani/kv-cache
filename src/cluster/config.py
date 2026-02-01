
NUM_SHARDS = 3

NODES = {
    1: {"host": "node1", "port": 7171},
    2: {"host": "node2", "port": 7171},
    3: {"host": "node3", "port": 7171},
}
SHARD_PRIMARY = {
    0: 1,
    1: 2,
    2: 3,
}
SHARD_REPLICA = {
    0: 3,
    1: 1,
    2: 2,
}


def get_shard_id(key: str) -> int:
    return hash(key) % NUM_SHARDS


def get_primary_node(shard_id: int) -> int:
    return SHARD_PRIMARY[shard_id]


def get_replica_node(shard_id: int) -> int:
    return SHARD_REPLICA[shard_id]
