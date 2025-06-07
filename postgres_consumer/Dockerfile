FROM python:3.12

WORKDIR /app

RUN pip install confluent-kafka psycopg2-binary

COPY consumer.py .

CMD ["python", "consumer.py"]