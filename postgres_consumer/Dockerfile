FROM python:3.12

WORKDIR /app

RUN pip install confluent-kafka psycopg2-binary

COPY consumer.py .
COPY wait-for-it.sh .

CMD ["./wait-for-it.sh", "postgres:5432", "--", "./wait-for-it.sh", "kafka:9092", "--", "python", "consumer.py"]