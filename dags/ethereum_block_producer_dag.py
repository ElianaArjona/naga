"""
Airflow DAG to stream Ethereum blocks into Kafka.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from airflow import DAG
from airflow.operators.python import PythonOperator
from confluent_kafka import Producer
from web3 import Web3, HTTPProvider
from web3.exceptions import BlockNotFound

from schemas.producer_schema import EthereumBlock  

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# DAG default args
default_args: Dict[str, Any] = {
    "start_date": datetime(2023, 1, 1),
}

# DAG definition
dag = DAG(
    "ethereum_block_producer",
    schedule_interval="*/1 * * * *",  # every minute
    catchup=False,
    default_args=default_args,
)

# Config: load from env variables
alchemy_api_key: Optional[str] = os.getenv("ALCHEMY_API_KEY")
if alchemy_api_key is None:
    raise ValueError("Missing Alchemy API key")

eth_rpc_url: str = f"https://eth-sepolia.g.alchemy.com/v2/{alchemy_api_key}"

kafka_broker: str = os.getenv("KAFKA_BROKER", "kafka:9092")
kafka_topic: str = os.getenv("KAFKA_TOPIC", "ethereum-blocks")

print(f"Using ETH RPC URL: {eth_rpc_url}")

def fetch_block_and_push_to_kafka() -> None:
    try:
        provider = HTTPProvider(eth_rpc_url, request_kwargs={"timeout": 10})
        web3 = Web3(provider)

        if not web3.is_connected():
            logger.error(f"Web3 is not connected to Ethereum node at {eth_rpc_url}")
            raise ConnectionError("Cannot connect to Ethereum RPC")

        latest_block_number: int = web3.eth.block_number
        logger.info(f"Latest block: {latest_block_number}")

        block = web3.eth.get_block(latest_block_number, full_transactions=False)

        # Extract the fields you want to validate
        logger.info(block)
        block_data = {
            "block_number": block.number,
            "block_hash": block.hash.hex(),
            "timestamp": block.timestamp,
            "miner": block.miner,
            "transactions": len(block.transactions)
        }

        # Validate via Pydantic
        validated_block = EthereumBlock(**block_data)

        # Serialize
        block_json = validated_block.model_dump_json()

        producer_conf: Dict[str, str] = {"bootstrap.servers": kafka_broker}
        producer = Producer(producer_conf)

        producer.produce(
            kafka_topic,
            key=str(validated_block.block_number).encode("utf-8"),
            value=block_json.encode("utf-8")
        )
        producer.flush()

        logger.info(f"Produced block {latest_block_number} to Kafka")

    except BlockNotFound as e:
        logger.error(f"Block not found: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")

# Airflow task
produce_task = PythonOperator(
    task_id="fetch_and_produce_block",
    python_callable=fetch_block_and_push_to_kafka,
    dag=dag,
)
