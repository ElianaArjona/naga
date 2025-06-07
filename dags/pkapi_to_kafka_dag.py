from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
from confluent_kafka import Producer
import json
import time

default_args = {
    'start_date': datetime(2023, 1, 1),
}

dag = DAG(
    'pokemon_partitioned_to_kafka_v2',
    schedule_interval='*/1 * * * *',
    catchup=False,
    default_args=default_args
)

def fetch_and_produce():
    producer = Producer({'bootstrap.servers': 'kafka:9092'})
    topic = 'pokemon-data-by-type'

    for i in range(1, 20):
        try:
            response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{i}/", timeout=5)
            response.raise_for_status()
            data = response.json()

            # Extract Pokemon type
            pokemon_type = data['types'][0]['type']['name']
            message = json.dumps(data)

            # Use type as key to control partitioning
            producer.produce(
                topic,
                key=pokemon_type.encode('utf-8'),
                value=message.encode('utf-8')
            )
            producer.flush()

            print(f"Produced: {data['name']} with key={pokemon_type}")

            time.sleep(0.2)

        except Exception as e:
            print(f"Error fetching Pokémon ID {i}: {e}")

produce_task = PythonOperator(
    task_id='fetch_pokemon_and_send_partitioned_to_kafka',
    python_callable=fetch_and_produce,
    dag=dag,
)
