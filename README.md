
# 🧪 Ethereum Blockchain Streaming Pipeline (Initial Version)

This project is an end-to-end data pipeline that streams live Ethereum blockchain data into Kafka and stores it into both PostgreSQL and ClickHouse for further analysis.

It uses:

- **Airflow**: Orchestrates the data ingestion
- **Kafka**: Acts as streaming data broker
- **Postgres**: Stores data for OLTP-style queries
- **ClickHouse**: Stores data for analytical queries
- **Docker Compose**: Containerizes the entire stack
- **Web3.py**: Connects to Ethereum blockchain
- **Alchemy RPC**: Provides blockchain node access

---

## ⚙️ Architecture

```
Ethereum Blockchain --> Web3.py (via Airflow DAG)
         |
         v
      Kafka (topic: ethereum-blocks)
         |
         v
   Kafka Consumers
     /        \
Postgres    ClickHouse
```

---

## 🚀 Components Overview

### 1️⃣ Airflow DAG

- Located inside `dags/ethereum_block_producer_dag.py`.
- Fetches the latest Ethereum block every minute.
- Publishes the full block data to Kafka (`ethereum-blocks` topic).
- Uses environment variables:
  - `ALCHEMY_API_KEY`: Your Alchemy access token.
  - `KAFKA_BROKER`: Kafka connection string.

### 2️⃣ Kafka

- Kafka broker runs inside Docker.
- Kafka topic used: `ethereum-blocks`.
- Topic is created manually using Kafka CLI inside docker.

### 3️⃣ PostgreSQL Consumer

- Consumes messages from Kafka.
- Extracts `block_number`, `block_hash`, `timestamp`.
- Stores them into `ethereum_blocks` table in Postgres.

### 4️⃣ ClickHouse Consumer

- Similar to Postgres consumer.
- Consumes from Kafka.
- Stores data into ClickHouse table `ethereum_blocks`.

---

## 🐳 Docker Compose Setup

All services are containerized:

- `airflow-webserver`
- `airflow-scheduler`
- `kafka`
- `zookeeper`
- `postgres`
- `clickhouse`
- `postgres-consumer`
- `clickhouse-consumer`
- (Optional) `kafka-tools` for Kafka CLI

---

## 🏗️ Usage Instructions

### 1️⃣ Clone the repository

```bash
git clone <repo-url>
cd project-folder
```

### 2️⃣ Setup `.env` file

Create `.env` file in project root with:

```env
# PostgreSQL
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow

# ClickHouse
CLICKHOUSE_DB=default
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=admin

# Airflow DB connection
AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow

# Airflow security key
AIRFLOW__CORE__FERNET_KEY=your_fernet_key

# Blockchain RPC Access
ALCHEMY_API_KEY=your_alchemy_api_key
```

---

### 3️⃣ Build & start containers

```bash
docker compose up --build -d
```

---

### 4️⃣ Create Kafka Topic

Enter Kafka CLI container:

```bash
docker compose exec kafka bash
```

Create topic:

```bash
kafka-topics --bootstrap-server kafka:9092 --create --topic ethereum-blocks --partitions 1 --replication-factor 1
```

---

### 5️⃣ Access Airflow

Open: [http://localhost:8080](http://localhost:8080)

Login credentials (default):

- user: `admin`
- pass: `admin` (or whatever you defined)

Trigger the `ethereum_block_producer` DAG manually.

---

### 6️⃣ Check consumers are working

- Consumers automatically subscribe to `ethereum-blocks`.
- Logs can be checked via:

```bash
docker compose logs clickhouse-consumer
docker compose logs postgres-consumer
```

---

### 7️⃣ Query data

**Postgres**

```bash
docker compose exec postgres psql -U airflow -d airflow

SELECT * FROM ethereum_blocks;
```

**ClickHouse**

```bash
docker compose exec clickhouse clickhouse-client

SELECT * FROM ethereum_blocks;
```

---

## 🐞 Common Issues

| Problem | Solution |
|---------|----------|
| Kafka DNS errors | Always use container names (e.g., `kafka:9092`) as brokers inside Docker network |
| Stale consumer code | Use `docker compose build --no-cache` |
| Airflow scheduler down | Restart `docker compose restart airflow-scheduler` |
| Kafka tools not available | Use dedicated `kafka-tools` container |

---

## 📦 TODO (for full production pipeline)

- [ ] Schema validation (pydantic or Avro)
- [ ] Partition strategy improvement
- [ ] Idempotency (upserts)
- [ ] Batching support for backfills
- [ ] Observability metrics
- [ ] Prometheus/Grafana integration

---

## 📌 Author's Note

This project is intentionally built as part of **Blockchain Data Engineering interview preparation**, demonstrating:

- Streaming pipeline architecture
- ETL orchestration via Airflow
- Kafka broker integration
- Consuming and processing blockchain data using Web3.py
- Real-life debugging experience with Dockerized pipelines

---

✅ ✅ ✅

# ✅ Next step: Upgrade to "Senior Interview Version"
