from __future__ import annotations

import json
import logging
import os
import time

from confluent_kafka import Consumer
import clickhouse_connect

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration (from environment)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "ethereum-blocks")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "admin")


def wait_for_clickhouse() -> clickhouse_connect.Client:  # type: ignore
    while True:
        try:
            client = clickhouse_connect.get_client(
                host=CLICKHOUSE_HOST,
                port=CLICKHOUSE_PORT,
                username=CLICKHOUSE_USER,
                password=CLICKHOUSE_PASSWORD,
            )
            client.ping()
            logger.info("Connected to ClickHouse")
            return client
        except Exception as e:
            logger.warning(f"Waiting for ClickHouse... {e}")
            time.sleep(3)


def wait_for_kafka() -> Consumer:
    while True:
        try:
            conf = {
                "bootstrap.servers": KAFKA_BROKER,
                "group.id": "clickhouse-consumer-group",
                "auto.offset.reset": "earliest",
            }
            consumer = Consumer(conf)
            logger.info("Connected to Kafka")
            return consumer
        except Exception as e:
            logger.warning(f"Waiting for Kafka... {e}")
            time.sleep(3)


def main() -> None:
    client = wait_for_clickhouse()

    client.command(
        """
        CREATE TABLE IF NOT EXISTS ethereum_blocks (
            block_number UInt64,
            block_hash String,
            timestamp DateTime
        ) ENGINE = MergeTree()
        ORDER BY block_number
    """
    )

    consumer = wait_for_kafka()
    consumer.subscribe([KAFKA_TOPIC])
    logger.info("ClickHouse consumer starting... (version 2025-06-08)")

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Kafka error: {msg.error()}")
            continue

        try:
            value = json.loads(msg.value().decode("utf-8"))
            if isinstance(value["number"], str):
                block_number = int(value["number"], 16)
                timestamp = int(value["timestamp"], 16)
            else:
                block_number = int(value["number"])
                timestamp = int(value["timestamp"])

            block_hash = value["hash"]

            client.insert(
                "ethereum_blocks",
                [(block_number, block_hash, timestamp)],
                column_names=["block_number", "block_hash", "timestamp"],
            )

            logger.info(f"Inserted block {block_number} into ClickHouse")

        except Exception as e:
            logger.exception(f"Processing error: {e}")

    consumer.close()


if __name__ == "__main__":
    main()
