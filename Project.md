Final Project: Distributed KV-Cache
===================================

Part A: My Implementation
---------------------------

### Architecture

In this project I took the Assignment-2 single-node KV-Cache and made it into a **3-node distributed KV-Cache cluster**.

Each node is running the same KV-Cache server code but has it's own unique `NODE_ID`
(I used environment variable for this). The cluster topology is static which means all nodes know about each other beforehand.

Clients can connect to **any node** they want in the cluster.  
Each node does the following things:

- Works as **PRIMARY** for some shards
- Works as **REPLICA** for some other shards
- Sends requests to the right node when its not responsible for that key
- Copies write operations to the replica node

All the communication between nodes uses the **same TCP protocol** that clients use.

---

### Sharding

Keys are distributed using **consistent hashing**:

shard_id=hash(key)%NUM_SHARDS


- Each shard has one **primary node** which is configured at start
- When node receives a request:
  - It calculates the shard ID from the key
  - If its **not the primary**, it forwards request to correct primary node
  - The primary node executes request and sends back response

This way clients don't need to know which node has which data, they can just connect to any node.

---

### Replication

Each shard gets replicated to **one replica node**.

For **write operations (PUT / DELETE)**:
1. Primary node does the write on its own storage first
2. Then primary sends same command to replica node
3. Client only gets success message after **both primary and replica finishes**

For **read operations (GET / EXISTS)**:
- Reads only happen on **primary node**
- Replicas don't serve reads to keep things simple

This makes sure writes are consistent and also provides backup incase primary fails.

### Challenges

One of the main challenge was routing requests correctly when clients could connect to **any node**,
even replica nodes. I handled this by making sure **every node calculates the shard and primary node**
for each key independently. So even if request comes to a replica or wrong node, it gets
forwarded to the correct primary safely. The primary then executes operation and does synchronous
replication to replica. This same routing logic on all nodes made the design simpler and made sure
everything works correctly without client needing to know which node owns what shard.

---

Part B: Beyond the Basics (Research Write-up)
---------------------------------------------

### 1. Failure Detection

Failure detection is basically figuring out if a node has crashed or stopped working.
A simple way is to send periodic heartbeat messages between nodes.
If a node doesn't respond within some time, we can assume its failed.

But the problem is its hard to tell if a node is just slow or actually crashed.
Networks can have delays and this causes false alarms sometimes.

Redis Cluster uses something called **gossip-based protocol** where nodes talk to eachother
and share health information. A node is only marked as failed when multiple nodes agrees,
this reduces wrong failure detections.

---

### 2. Automatic Failover

If primary node crashes, the replica needs to become the new primary.
This needs coordination so that all nodes agree on whose the new primary.

Failover can cause problems like **split-brain**, where two nodes think they
are both primary. To avoid this systems usually need majority of nodes to agree.

Redis Cluster uses voting mechanism where replicas vote to choose
a new primary, making sure only one node becomes primary.

---

### 3. Consistency vs Availability Trade-offs

My implementation uses **synchronous replication**, which means consistency is more important.
A write only succeeds after both primary and replica confirms the operation.

With **asynchronous replication**, writes return immediately after primary saves
the data. This is faster and more available but you can loose data if
primary crashes before replica gets the update.

Redis Cluster tries to balance both by providing strong consistency for
single-key operations but accepts some inconsistency during failover,
this shows the CAP theorem tradeoffs.