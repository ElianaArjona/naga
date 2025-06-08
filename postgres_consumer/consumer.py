from __future__ import annotations

import json
import logging
import os
import time

from confluent_kafka import Consumer
import psycopg2
from psycopg2.extensions import connection

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
                'bootstrap.servers': KAFKA_BROKER,
                'group.id': 'postgres-consumer-group',
                'auto.offset.reset': 'earliest',
            }
            consumer = Consumer(conf)
            logger.info("Connected to Kafka")
            return consumer
        except Exception as e:
            logger.warning(f"Waiting for Kafka... {e}")
            time.sleep(3)


def main() -> None:
    pg_conn = wait_for_postgres()
    cursor = pg_conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ethereum_blocks (
            block_number BIGINT PRIMARY KEY,
            block_hash TEXT,
            timestamp TIMESTAMP
        )
    """)
    pg_conn.commit()

    consumer = wait_for_kafka()
    consumer.subscribe([KAFKA_TOPIC])

    logger.info("Postgres consumer starting... (version 2025-06-08)")

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Kafka error: {msg.error()}")
            continue

        try:
            value = json.loads(msg.value().decode('utf-8'))
            if isinstance(value['number'], str):
                block_number = int(value['number'], 16)
                timestamp = int(value['timestamp'], 16)
            else:
                block_number = int(value['number'])
                timestamp = int(value['timestamp'])
            
            block_hash = value['hash']

            cursor.execute(
                """
                INSERT INTO ethereum_blocks (block_number, block_hash, timestamp)
                VALUES (%s, %s, to_timestamp(%s))
                ON CONFLICT (block_number) DO NOTHING
                """,
                (block_number, block_hash, timestamp),
            )
            pg_conn.commit()

            logger.info(f"Inserted block {block_number}")

        except Exception as e:
            logger.exception(f"Processing error: {e}")

    consumer.close()


if __name__ == "__main__":
    main()
