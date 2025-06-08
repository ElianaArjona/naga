"""
Airflow DAG to stream Ethereum blocks into Kafka.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from confluent_kafka import Producer
from web3 import Web3, HTTPProvider
from web3.exceptions import BlockNotFound

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# DAG default args
default_args = {
    'start_date': datetime(2023, 1, 1),
}

# DAG definition
dag = DAG(
    'ethereum_block_producer',
    schedule_interval='*/1 * * * *',  # every minute
    catchup=False,
    default_args=default_args
)

# Config: you can also load this from env variables
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
if not ALCHEMY_API_KEY:
    raise ValueError("Missing Alchemy API key")

ETH_RPC_URL = f"https://eth-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

KAFKA_BROKER: str = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC", "ethereum-blocks")

print(f"Using ETH RPC URL: {ETH_RPC_URL}")

def fetch_block_and_push_to_kafka() -> None:
    try:
        # Initialize Web3 with better HTTPProvider handling
        provider = HTTPProvider(ETH_RPC_URL, request_kwargs={'timeout': 10})
        web3 = Web3(provider)

        # Sanity check
        if not web3.is_connected():
            logger.error(f"Web3 is not connected to Ethereum node at {ETH_RPC_URL}")
            raise ConnectionError("Cannot connect to Ethereum RPC")

        latest_block_number: int = web3.eth.block_number
        logger.info(f"Latest block: {latest_block_number}")

        # Fetch block with full transactions
        block = web3.eth.get_block(latest_block_number, full_transactions=True)
        block_data: dict = dict(block)

        # Use web3.to_json instead of json.dumps for better encoding
        block_json: str = json.dumps(block_data, default=str)

        # Kafka producer
        producer_conf = {'bootstrap.servers': KAFKA_BROKER}
        producer = Producer(producer_conf)

        producer.produce(KAFKA_TOPIC, value=block_json.encode('utf-8'))
        producer.flush()

        logger.info(f"Produced block {latest_block_number} to Kafka")

    except BlockNotFound as e:
        logger.error(f"Block not found: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")

# Airflow task
produce_task = PythonOperator(
    task_id='fetch_and_produce_block',
    python_callable=fetch_block_and_push_to_kafka,
    dag=dag,
)
