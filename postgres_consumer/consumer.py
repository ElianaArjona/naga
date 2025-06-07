import json
import psycopg2
from confluent_kafka import Consumer

# Kafka Consumer config
kafka_conf = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'postgres-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(kafka_conf)
consumer.subscribe(['pokemon-data-by-type'])

# Postgres connection
pg_conn = psycopg2.connect(
    host='postgres',
    dbname='airflow',
    user='airflow',
    password='airflow'
)
cursor = pg_conn.cursor()

# Create table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pokemon_data (
        name TEXT,
        type TEXT
    )
""")
pg_conn.commit()

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print("Consumer error: {}".format(msg.error()))
        continue

    value = json.loads(msg.value().decode('utf-8'))
    key = msg.key().decode('utf-8') if msg.key() else None

    name = value['name']
    pokemon_type = key

    cursor.execute("INSERT INTO pokemon_data (name, type) VALUES (%s, %s)", (name, pokemon_type))
    pg_conn.commit()

    print(f"Inserted {name} of type {pokemon_type} into Postgres.")

consumer.close()
