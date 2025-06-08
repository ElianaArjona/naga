from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime

from confluent_kafka import Consumer
import clickhouse_connect
from prometheus_client import start_http_server, Counter, Histogram

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

# Metrics definitions (initialized early)
MESSAGES_CONSUMED = Counter("messages_consumed_total", "Total messages consumed")
MESSAGES_FAILED = Counter("messages_failed_total", "Total failed messages")
BATCH_SIZE = Histogram("batch_size", "Number of messages in batch", buckets=[1, 5, 10, 20, 50, 100, 200])
PROCESSING_TIME = Histogram("processing_time_seconds", "Time spent processing batch")

# Start Prometheus HTTP server
start_http_server(8000)

def wait_for_clickhouse() -> clickhouse_connect.Client:
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


def initialize_counters_from_clickhouse(client: clickhouse_connect.Client) -> None:
    """Recover previously inserted rows to initialize Prometheus counters"""
    try:
        result = client.query("SELECT COUNT(*) FROM ethereum_blocks")
        starting_count = result.result_rows[0][0]
        logger.info(f"Initializing consumed counter with existing ClickHouse rows: {starting_count}")
        MESSAGES_CONSUMED.inc(starting_count)
    except Exception as e:
        logger.warning(f"Failed to initialize counters from ClickHouse: {e}")


def main() -> None:
    client = wait_for_clickhouse()

    # Create table if it doesn't exist (idempotent)
    client.command(
        """
        CREATE TABLE IF NOT EXISTS ethereum_blocks (
            block_number UInt64,
            block_hash String,
            timestamp DateTime,
            transactions UInt32,
            miner String
        ) ENGINE = ReplacingMergeTree()
        ORDER BY block_number
        """
    )

    # Initialize Prometheus counters from ClickHouse state
    initialize_counters_from_clickhouse(client)

    consumer = wait_for_kafka()
    consumer.subscribe([KAFKA_TOPIC])
    time.sleep(5)

    while True:
        msgs = consumer.consume(10, timeout=1.0)
        batch_len = len(msgs)
        BATCH_SIZE.observe(batch_len)

        if not msgs:
            continue

        with PROCESSING_TIME.time():
            rows = []
            success_count = 0

            for msg in msgs:
                logger.info(f"Polled {len(msgs)} messages from Kafka")

                if msg.error():
                    logger.error(f"Kafka error: {msg.error()}")
                    MESSAGES_FAILED.inc()
                    continue

                try:
                    value = json.loads(msg.value().decode("utf-8"))
                    block_number = int(value["block_number"])
                    timestamp_str = value["timestamp"]
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    block_hash = value["block_hash"]
                    transactions = int(value["transactions"])
                    miner = value["miner"]

                    rows.append((block_number, block_hash, timestamp, transactions, miner))
                    success_count += 1

                except Exception as e:
                    logger.exception(f"Processing error: {e}")
                    MESSAGES_FAILED.inc()

            if rows:
                client.insert(
                    "ethereum_blocks",
                    rows,
                    column_names=["block_number", "block_hash", "timestamp", "transactions", "miner"],
                )
                logger.info(f"Inserted {len(rows)} rows into ClickHouse")

            # Update Prometheus counter after successful batch insert
            MESSAGES_CONSUMED.inc(success_count)


if __name__ == "__main__":
    main()
