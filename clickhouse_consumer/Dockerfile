FROM python:3.12

WORKDIR /app

RUN pip install confluent-kafka clickhouse-connect

COPY consumer.py .
COPY wait-for-it.sh .
RUN chmod +x wait-for-it.sh

# Start only after ClickHouse and Kafka are ready
CMD ["./wait-for-it.sh", "clickhouse:8123", "--", "./wait-for-it.sh", "kafka:9092", "--", "python", "consumer.py"]