# 🐙 Naga Project — Streaming Data Pipeline with Airflow, Kafka, ClickHouse & PostgreSQL

---

## 🧭 Project Overview

**Naga** is a modern, highly scalable streaming data pipeline architecture designed to process, transform, and store real-time data at scale. This project integrates multiple distributed systems following a microservices approach, orchestrated with Docker and deployed serverlessly on Render.

---

## 🔥 Key Components

- **Apache Airflow** — Workflow orchestration and DAG scheduling.
- **Apache Kafka** — Real-time event streaming platform and distributed message broker.
- **ClickHouse** — Column-oriented OLAP database for high-performance analytical queries.
- **PostgreSQL** — Relational database for transactional data and Airflow metadata.
- **Python Kafka Consumers** — Services that consume streaming data and write into PostgreSQL and ClickHouse.
- **Docker Compose** — Complete local development stack.
- **Render** — Fully managed serverless cloud deployment.

---

## 🌐 High-Level Architecture

```text
+----------------+      +--------------+      +-----------------+
|  API Producer  | ---> |    Kafka     | ---> |  Kafka Consumers |
+----------------+      +--------------+      +-----------------+
                                                  |           |
                                               +--+--+     +--+--+
                                               |Postgres|  |ClickHouse|
                                               +-------+   +--------+
```

- **Producers:** Airflow DAGs collect external data sources (e.g. Star Wars API, Pokémon API), stream data into Kafka topics.
- **Consumers:** Python microservices consume Kafka topics and write transformed data into PostgreSQL and ClickHouse for storage and analytics.
- **Storage:** PostgreSQL for structured transactional data, ClickHouse for analytics.

---

## 🚀 Deployment Modes

- ✅ **Local Development:** Docker Compose powered full-stack for local development.
- ✅ **Production Deployment:** Fully serverless Render deployment using Render Blueprints (`render.yaml`).

---

## 🐳 Local Development Setup

### ✅ Prerequisites

- Docker installed
- Docker Compose installed
- Python 3.12 installed (optional for local scripts)

### ✅ Clone and Launch

```bash
git clone https://github.com/YOUR-ORG/naga.git
cd naga
docker-compose up --build
```

This will launch:

- Airflow Webserver (http://localhost:8080)
- Airflow Scheduler
- Kafka Broker
- Zookeeper
- ClickHouse DB
- PostgreSQL DB
- Kafka Consumers (Postgres & ClickHouse)

---

## 📂 Local Development File Structure

```text
naga/
│
├── dags/                    # Airflow DAGs
├── docker-compose.yml       # Local Docker Compose definition
├── Dockerfile.airflow       # Custom Airflow Docker build
│
├── postgres_consumer/       # Postgres Kafka consumer microservice
│   ├── Dockerfile
│   └── consumer.py
│
├── clickhouse_consumer/     # ClickHouse Kafka consumer microservice
│   ├── Dockerfile
│   └── consumer.py
│
└── render.yaml              # Render cloud deployment blueprint
```

---

## 🚀 Cloud Deployment on Render

This project leverages **Render Blueprints** to fully automate infrastructure deployment via the `render.yaml` file.

### ✅ Render Deployment Steps

1️⃣ **Connect your GitHub repo to Render**

2️⃣ In Render, select **Blueprint Deploy** and pick your branch.

3️⃣ Render will automatically deploy:

- Airflow Webserver (Web service)
- Airflow Scheduler (Worker)
- Postgres Consumer (Worker)
- ClickHouse Consumer (Worker)
- Kafka (Worker using public Docker image)
- Zookeeper (Worker using public Docker image)
- ClickHouse (Worker using public Docker image)

4️⃣ ✅ Create Managed PostgreSQL instance via Render UI:
- Database Name: `airflow`
- Username: `airflow`
- Password: `airflow` (or a strong password)
- Internal Hostname: e.g. `postgres-db:5432` for Render DNS

5️⃣ ✅ Create Environment Group (`.env`) in Render with the following environment variables:

| Variable | Value |
|----------|-------|
| POSTGRES_USER | airflow |
| POSTGRES_PASSWORD | airflow |
| POSTGRES_DB | airflow |
| CLICKHOUSE_DB | default |
| CLICKHOUSE_USER | default |
| CLICKHOUSE_PASSWORD | admin |
| KAFKA_BROKER_ID | 1 |
| AIRFLOW_USER | admin |
| AIRFLOW_PASSWORD | admin |
| AIRFLOW_EMAIL | admin@example.com |
| AIRFLOW__CORE__FERNET_KEY | (generate one: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| AIRFLOW__CORE__SQL_ALCHEMY_CONN | postgresql+psycopg2://airflow:airflow@postgres-db:5432/airflow |

---

## ⚙️ Docker Build Contexts Summary

| Service | Build Context | Dockerfile |
|---------|----------------|------------|
| Airflow Webserver | `./` | `Dockerfile.airflow` |
| Airflow Scheduler | `./` | `Dockerfile.airflow` |
| Postgres Consumer | `./postgres_consumer/` | `Dockerfile` |
| ClickHouse Consumer | `./clickhouse_consumer/` | `Dockerfile` |

---

## 📡 Render Internal DNS Communication

| Service | Internal DNS |
|---------|---------------|
| Kafka | `kafka:9092` |
| Zookeeper | `zookeeper:2181` |
| ClickHouse | `clickhouse:8123` |
| Postgres | `postgres-db:5432` |

Render manages DNS resolution automatically between services.

---

## 🏗 render.yaml Summary

The `render.yaml` defines full infrastructure-as-code deployment:

- ✅ 1x Web Service (Airflow Webserver)
- ✅ 6x Workers (Scheduler, Consumers, Kafka, Zookeeper, ClickHouse)

All services are independently scalable and isolated.

---

## 🧪 Testing Kafka Consumers

- Data is pushed into Kafka topics:
  - `pokemon-data`
  - `pokemon-data-by-type`
- Kafka consumers automatically consume, transform and write data into:
  - PostgreSQL
  - ClickHouse

You can manually trigger DAGs in Airflow UI for data ingestion.

---

## 🏷 Design Goals

- Fully event-driven
- Microservices architecture
- Streaming-first design
- Stateless deployment (except data layers)
- Cloud-native & scalable
- Serverless Render deployment (no dedicated DevOps needed)

---

## ⚠️ Known Limitations

- Kafka partitioning is managed in producer logic based on Pokémon type.
- Managed PostgreSQL must be manually provisioned in Render UI.
- Proper resource sizing depends on production data load.
- Internal DNS names must be used between services.

---

## 🚀 CI/CD Deployment Flow

- ✅ All deployment is automated through Render Blueprints.
- ✅ Any commit to the repo auto-triggers new deployments.
- ✅ Secrets and configurations are securely managed via Render Environment Groups.

---

## 📄 License

This project is licensed for educational & prototyping purposes.

---

**Enjoy your fully distributed streaming microservices pipeline — cloud-native and fully serverless. 🚀**

