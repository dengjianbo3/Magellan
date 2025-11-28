"""
Kafka Client
Kafka 客户端

提供统一的 Kafka 生产者/消费者接口
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_CLIENT_ID = os.getenv("KAFKA_CLIENT_ID", "magellan-client")

# 尝试导入 aiokafka，如果不可用则使用 mock
try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    KAFKA_AVAILABLE = True
except ImportError:
    logger.warning("aiokafka not installed, Kafka functionality will be disabled")
    KAFKA_AVAILABLE = False
    AIOKafkaProducer = None
    AIOKafkaConsumer = None

from .messages import MagellanMessage
from .topics import MagellanTopics, get_partition_key


class KafkaClient:
    """
    Kafka 客户端

    提供异步的消息生产和消费能力
    """

    _instance: Optional['KafkaClient'] = None
    _producer: Optional[Any] = None
    _consumers: Dict[str, Any] = {}
    _running: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._fallback_queue: asyncio.Queue = asyncio.Queue()  # 降级队列

    @property
    def is_available(self) -> bool:
        """检查 Kafka 是否可用"""
        return KAFKA_AVAILABLE and self._producer is not None

    async def start(self):
        """启动 Kafka 客户端"""
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka not available, using fallback mode")
            return

        if self._running:
            return

        try:
            # 创建生产者
            self._producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                client_id=KAFKA_CLIENT_ID,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all'  # 等待所有副本确认
            )
            await self._producer.start()
            self._running = True
            logger.info(f"Kafka producer started, connected to {KAFKA_BOOTSTRAP_SERVERS}")

        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self._producer = None

    async def stop(self):
        """停止 Kafka 客户端"""
        self._running = False

        # 停止所有消费者
        for consumer in self._consumers.values():
            await consumer.stop()
        self._consumers.clear()

        # 停止生产者
        if self._producer:
            await self._producer.stop()
            self._producer = None

        logger.info("Kafka client stopped")

    async def send(
        self,
        topic: MagellanTopics,
        message: MagellanMessage,
        key: str = None
    ) -> bool:
        """
        发送消息到指定 Topic

        Args:
            topic: 目标 Topic
            message: 消息对象
            key: 分区键（可选，自动从消息中提取）

        Returns:
            是否发送成功
        """
        if not self.is_available:
            # 降级到内存队列
            logger.debug(f"Kafka unavailable, queueing message to fallback")
            await self._fallback_queue.put({
                "topic": topic.value,
                "message": message.model_dump(),
                "timestamp": datetime.now().isoformat()
            })
            return True

        try:
            # 获取分区键
            if not key:
                key = get_partition_key(topic, message.model_dump())

            # 发送消息
            await self._producer.send_and_wait(
                topic.value,
                value=message.model_dump(),
                key=key
            )

            logger.debug(f"Message sent to {topic.value}: {message.message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message to {topic.value}: {e}")
            # 降级到内存队列
            await self._fallback_queue.put({
                "topic": topic.value,
                "message": message.model_dump(),
                "timestamp": datetime.now().isoformat()
            })
            return False

    async def send_batch(
        self,
        topic: MagellanTopics,
        messages: List[MagellanMessage]
    ) -> int:
        """
        批量发送消息

        Args:
            topic: 目标 Topic
            messages: 消息列表

        Returns:
            成功发送的消息数量
        """
        success_count = 0
        for msg in messages:
            if await self.send(topic, msg):
                success_count += 1
        return success_count

    async def subscribe(
        self,
        topic: MagellanTopics,
        group_id: str,
        handler: Callable[[MagellanMessage], Awaitable[None]]
    ):
        """
        订阅 Topic 并注册消息处理器

        Args:
            topic: 要订阅的 Topic
            group_id: 消费者组 ID
            handler: 异步消息处理函数
        """
        # 注册处理器
        if topic.value not in self._message_handlers:
            self._message_handlers[topic.value] = []
        self._message_handlers[topic.value].append(handler)

        if not KAFKA_AVAILABLE:
            logger.warning(f"Kafka unavailable, handler for {topic.value} registered but won't receive Kafka messages")
            return

        # 如果该 Topic 还没有消费者，创建一个
        consumer_key = f"{topic.value}:{group_id}"
        if consumer_key not in self._consumers:
            try:
                consumer = AIOKafkaConsumer(
                    topic.value,
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    group_id=group_id,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000
                )
                await consumer.start()
                self._consumers[consumer_key] = consumer

                # 启动消费循环
                asyncio.create_task(self._consume_loop(consumer_key))

                logger.info(f"Subscribed to {topic.value} with group {group_id}")

            except Exception as e:
                logger.error(f"Failed to subscribe to {topic.value}: {e}")

    async def _consume_loop(self, consumer_key: str):
        """消费循环"""
        consumer = self._consumers.get(consumer_key)
        if not consumer:
            return

        topic = consumer_key.split(":")[0]

        try:
            async for msg in consumer:
                if not self._running:
                    break

                handlers = self._message_handlers.get(topic, [])
                for handler in handlers:
                    try:
                        # Phase 7: 直接传递原始 dict 给处理器
                        # 让处理器根据 topic 类型重建正确的消息类型
                        await handler(msg.value)
                    except Exception as e:
                        logger.error(f"Handler error for {topic}: {e}")

        except Exception as e:
            logger.error(f"Consumer loop error for {topic}: {e}")

    async def get_fallback_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取降级队列中的消息

        用于 Kafka 恢复后补发消息

        Args:
            limit: 最大获取数量

        Returns:
            消息列表
        """
        messages = []
        while not self._fallback_queue.empty() and len(messages) < limit:
            try:
                msg = self._fallback_queue.get_nowait()
                messages.append(msg)
            except asyncio.QueueEmpty:
                break
        return messages

    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return {
            "kafka_available": KAFKA_AVAILABLE,
            "producer_connected": self._producer is not None,
            "running": self._running,
            "consumers_count": len(self._consumers),
            "handlers_count": sum(len(h) for h in self._message_handlers.values()),
            "fallback_queue_size": self._fallback_queue.qsize()
        }


# 单例访问
_kafka_client: Optional[KafkaClient] = None


def get_kafka_client() -> KafkaClient:
    """获取 Kafka 客户端单例"""
    global _kafka_client
    if _kafka_client is None:
        _kafka_client = KafkaClient()
    return _kafka_client


async def init_kafka():
    """初始化 Kafka 客户端"""
    client = get_kafka_client()
    await client.start()
    return client


async def close_kafka():
    """关闭 Kafka 客户端"""
    client = get_kafka_client()
    await client.stop()
