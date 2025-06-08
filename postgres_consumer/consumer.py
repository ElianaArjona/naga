from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime

from confluent_kafka import Consumer
import psycopg2
from psycopg2.extensions import connection
from prometheus_client import start_http_server, Counter, Histogram

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration (from environment)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "ethereum-blocks")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "airflow")
POSTGRES_USER = os.getenv("POSTGRES_USER", "airflow")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")

# Metrics definitions
MESSAGES_CONSUMED = Counter("messages_consumed_total", "Total messages consumed")
MESSAGES_FAILED = Counter("messages_failed_total", "Total failed messages")
BATCH_SIZE = Histogram("batch_size", "Number of messages in batch", buckets=[1, 5, 10, 20, 50, 100, 200])
PROCESSING_TIME = Histogram("processing_time_seconds", "Time spent processing batch")

# Start Prometheus metrics server
start_http_server(8000)

def wait_for_postgres() -> connection:
    while True:
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
            )
            logger.info("Connected to Postgres")
            return conn
        except Exception as e:
            logger.warning(f"Waiting for Postgres... {e}")
            time.sleep(3)


def wait_for_kafka() -> Consumer:
    while True:
        try:
            conf = {
                "bootstrap.servers": KAFKA_BROKER,
                "group.id": "postgres-consumer-group",
                "auto.offset.reset": "earliest",
            }
            consumer = Consumer(conf)
            logger.info("Connected to Kafka")
            return consumer
        except Exception as e:
            logger.warning(f"Waiting for Kafka... {e}")
            time.sleep(3)


def initialize_counters_from_postgres(conn: connection) -> None:
    """Initialize Prometheus counters based on existing rows in Postgres"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ethereum_blocks")
        count = cursor.fetchone()[0]
        logger.info(f"Initializing consumed counter from Postgres rows: {count}")
        MESSAGES_CONSUMED.inc(count)
    except Exception as e:
        logger.warning(f"Failed to initialize counters from Postgres: {e}")


def main() -> None:
    pg_conn = wait_for_postgres()
    cursor = pg_conn.cursor()

    # Create table if not exists (idempotent)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ethereum_blocks (
            block_number BIGINT PRIMARY KEY,
            block_hash TEXT,
            timestamp TIMESTAMP,
            transactions INTEGER,
            miner TEXT
        )
    """)
    pg_conn.commit()

    # Initialize counters from current DB state
    initialize_counters_from_postgres(pg_conn)

    consumer = wait_for_kafka()
    consumer.subscribe([KAFKA_TOPIC])
    time.sleep(5)

    logger.info("Postgres consumer starting... (production version)")

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
                cursor.executemany(
                    """
                    INSERT INTO ethereum_blocks (block_number, block_hash, timestamp, transactions, miner)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (block_number) DO UPDATE
                    SET block_hash = EXCLUDED.block_hash,
                        timestamp = EXCLUDED.timestamp,
                        transactions = EXCLUDED.transactions,
                        miner = EXCLUDED.miner
                    """,
                    rows,
                )
                pg_conn.commit()
                logger.info(f"Inserted {len(rows)} rows into Postgres")

            # Update Prometheus counter after successful batch
            MESSAGES_CONSUMED.inc(success_count)


if __name__ == "__main__":
    main()
