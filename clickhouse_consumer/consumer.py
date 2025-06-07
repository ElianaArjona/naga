import json
from confluent_kafka import Consumer
import clickhouse_connect

# Kafka Consumer config
kafka_conf = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'clickhouse-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(kafka_conf)
consumer.subscribe(['pokemon-data-by-type'])

# ClickHouse connection
client = clickhouse_connect.get_client(
    host='clickhouse',
    port=8123,
    username='default',
    password='admin'
)

# Create table if not exists
client.command("""
CREATE TABLE IF NOT EXISTS pokemon_data (
    name String,
    type String
) ENGINE = MergeTree()
ORDER BY (type, name)
""")

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

    client.insert('pokemon_data', [(name, pokemon_type)])

    print(f"Inserted {name} of type {pokemon_type} into ClickHouse.")

consumer.close()
