from typing import Iterator

from redis import Redis
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    CheckpointTuple,
    WRITES_IDX_MAP,
    get_checkpoint_id,
    get_checkpoint_metadata,
)


class RedisCheckpointer(BaseCheckpointSaver):
    """Checkpointer de LangGraph usando Redis/Memurai básico."""

    def __init__(self, redis_client: Redis):
        super().__init__()
        self.redis = redis_client

    def _prefix(self, thread_id, checkpoint_ns):
        return f"lgcp:{thread_id}:{checkpoint_ns}"

    def _checkpoint_key(self, thread_id, checkpoint_ns, checkpoint_id):
        return f"{self._prefix(thread_id, checkpoint_ns)}:cp:{checkpoint_id}"

    def _writes_key(self, thread_id, checkpoint_ns, checkpoint_id):
        return f"{self._prefix(thread_id, checkpoint_ns)}:writes:{checkpoint_id}"

    def _encode(self, value):
        type_name, data = self.serde.dumps_typed(value)
        return type_name.encode() + b"\0" + data

    def _decode(self, value):
        type_name, data = value.split(b"\0", 1)
        return self.serde.loads_typed((type_name.decode(), data))

    def get_tuple(self, config):
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        if checkpoint_id:
            key = self._checkpoint_key(
                thread_id, checkpoint_ns, checkpoint_id
            )
        else:
            pattern = f"{self._prefix(thread_id, checkpoint_ns)}:cp:*"
            keys = list(self.redis.scan_iter(match=pattern))

            if not keys:
                return None

            key = max(
                keys,
                key=lambda item: item.decode().rsplit(":cp:", 1)[-1]
            )

        data = self.redis.hgetall(key)

        if not data:
            return None

        checkpoint = self._decode(data[b"checkpoint"])
        metadata = self._decode(data[b"metadata"])
        parent_id = data.get(b"parent_id", b"").decode()

        writes_key = self._writes_key(
            thread_id, checkpoint_ns, checkpoint["id"]
        )

        raw_writes = self.redis.hgetall(writes_key)
        pending_writes = []

        for raw in raw_writes.values():
            task_id, channel, value, task_path = self._decode(raw)
            pending_writes.append((task_id, channel, value))

        actual_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

        parent_config = None

        if parent_id:
            parent_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": parent_id,
                }
            }

        return CheckpointTuple(
            config=actual_config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=pending_writes,
        )

    def put(self, config, checkpoint, metadata, new_versions):
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]

        key = self._checkpoint_key(
            thread_id, checkpoint_ns, checkpoint_id
        )

        parent_id = configurable.get("checkpoint_id", "")

        self.redis.hset(
            key,
            mapping={
                "checkpoint": self._encode(checkpoint),
                "metadata": self._encode(
                    get_checkpoint_metadata(config, metadata)
                ),
                "parent_id": parent_id,
            },
        )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(self, config, writes, task_id, task_path=""):
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable["checkpoint_id"]

        key = self._writes_key(
            thread_id, checkpoint_ns, checkpoint_id
        )

        for index, (channel, value) in enumerate(writes):
            write_index = WRITES_IDX_MAP.get(channel, index)
            field = f"{task_id}:{write_index}"

            self.redis.hset(
                key,
                field,
                self._encode((task_id, channel, value, task_path)),
            )

    def list(
        self,
        config=None,
        *,
        filter=None,
        before=None,
        limit=None,
    ) -> Iterator[CheckpointTuple]:

        if config:
            configurable = config["configurable"]
            thread_id = configurable["thread_id"]
            checkpoint_ns = configurable.get("checkpoint_ns", "")
            pattern = f"{self._prefix(thread_id, checkpoint_ns)}:cp:*"
        else:
            pattern = "lgcp:*:cp:*"

        keys = sorted(
            self.redis.scan_iter(match=pattern),
            key=lambda item: item.decode().rsplit(":cp:", 1)[-1],
            reverse=True,
        )

        count = 0

        for key in keys:
            decoded_key = key.decode()
            prefix, checkpoint_id = decoded_key.rsplit(":cp:", 1)

            if before:
                before_id = get_checkpoint_id(before)
                if before_id and checkpoint_id >= before_id:
                    continue

            if config and get_checkpoint_id(config):
                if checkpoint_id != get_checkpoint_id(config):
                    continue

            remaining = prefix[len("lgcp:"):]
            thread_id, separator, checkpoint_ns = remaining.partition(":")

            item_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns if separator else "",
                    "checkpoint_id": checkpoint_id,
                }
            }

            item = self.get_tuple(item_config)

            if item is None:
                continue

            if filter and not all(
                item.metadata.get(k) == v for k, v in filter.items()
            ):
                continue

            yield item
            count += 1

            if limit is not None and count >= limit:
                break

    def delete_thread(self, thread_id):
        pattern = f"lgcp:{thread_id}:*"
        keys = list(self.redis.scan_iter(match=pattern))

        if keys:
            self.redis.delete(*keys)
