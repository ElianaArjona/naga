from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from confluent_kafka import Producer

default_args = {
    'start_date': datetime(2023, 1, 1),
}

dag = DAG(
    'kafka_producer_dag',
    schedule_interval=None,
    catchup=False,
    default_args=default_args
)

def produce_to_kafka():
    p = Producer({'bootstrap.servers': 'kafka:9092'})
    topic = 'my-test-topic'
    
    for i in range(5):
        message = f"Message {i} from Airflow"
        p.produce(topic, message.encode('utf-8'))
        p.flush()
        print(f"Produced: {message}")

produce_task = PythonOperator(
    task_id='produce_task',
    python_callable=produce_to_kafka,
    dag=dag,
)
