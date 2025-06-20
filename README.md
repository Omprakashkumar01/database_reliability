## PostgreSQL Logical Replication Setup (Master-Replica)
This repository contains a Docker Compose setup for demonstrating PostgreSQL logical replication between a master and a replica instance. It includes scripts for database initialization, schema creation, sample data insertion, and a robust setup script to manage the replication configuration.

![image](https://github.com/user-attachments/assets/5bef9a44-b8e7-4576-8d8f-3c418befe4a8)


## Project Structure
.
├── docker-compose.yml
├── master_config/
│   └── postgresql.conf
├── master_entrypoint.sh
├── init_master.sql
├── init_replica.sql
├── setup_replication.py
└── insert_data.py

## Files Explanation
# docker-compose.yml:
Defines two PostgreSQL services, pg_master and pg_replica.

# pg_master: 
Configured as the publisher, with custom postgresql.conf and a custom entrypoint to ensure wal_level = logical is properly applied.

# pg_replica: 
Configured as the subscriber, depending on pg_master's health.

# master_config/postgresql.conf: 
Custom configuration for pg_master to enable logical replication (wal_level = logical, max_replication_slots, max_wal_senders).

# master_entrypoint.sh: 
A custom shell script used as the entrypoint for the pg_master container. It ensures initdb is run correctly if the data directory is empty and that the custom postgresql.conf is copied and applied before the PostgreSQL server starts. This addresses specific timing and permission issues within the Docker environment.

# init_master.sql: 
A SQL script that the pg_master container runs on its initial startup. It creates the testDB database and the orders table.

# init_replica.sql: 
A SQL script that the pg_replica container runs on its initial startup. It creates the testDB database and the orders table. Crucially, the CREATE SUBSCRIPTION command is NOT here anymore; it's handled by setup_replication.py.

# setup_replication.py: 
* A Python script responsible for orchestrating the advanced setup steps that require precise timing and connection management:

* Ensures testDB and orders table exist on both master and replica.

* Explicitly creates the my_publication on pg_master.

* Crucially, it waits until pg_master's wal_level is confirmed as 'logical'.

* Creates the my_subscription on pg_replica, connecting to pg_master.

* Uses psycopg2 in autocommit mode for database-level operations (DROP DATABASE, CREATE DATABASE, CREATE PUBLICATION, CREATE SUBSCRIPTION) that cannot run within standard transactions.

# insert_data.py: 
A Python script to:

* Insert sample data into the orders table on pg_master.

* Fetch and display data from both pg_master and pg_replica.

* Validate that the data has been successfully replicated from master to replica.

# Setup and Running Instructions
Follow these steps to deploy and test the PostgreSQL logical replication setup:

# Prerequisites
* Docker and Docker Compose installed on your system (e.g., EC2 instance).

* Python 3 and pip installed.

* psycopg2-binary Python package installed:
```
pip3 install psycopg2-binary
```



1. Make the Custom Entrypoint Executable
```
chmod +x master_entrypoint.sh
```
2. Start the Docker Containers
Navigate to the root directory of the project (where docker-compose.yml is located) and run:
```
docker compose down --volumes # Optional, but recommended for a clean start
docker compose up --build -d
```
This command will build (if necessary) and start the pg_master and pg_replica containers in the background.

3. Run the Replication Setup Script
Once the containers are up and running (allow some time for them to initialize, typically a minute or two), execute the setup script:
```
python3 setup_replication.py
```
This script will manage the creation of databases/tables, publication, and subscription, including waiting for pg_master's wal_level to be correctly set. You will see detailed output about its progress.

4. Insert Data and Validate Replication
After the setup_replication.py script completes successfully, run the data insertion and validation script:
```
python3 insert_data.py
```
This script will insert sample data into the master and then verify that it has been replicated to the replica. You should see output confirming Validation successful: Data on pg_master and pg_replica are identical!.

# Verification
To manually verify the setup:

1. Connect to pg_master (host port 5432):
```
psql -h localhost -p 5432 -U testuser -d testDB
```
Inside psql, check SHOW wal_level; (should be logical) and \dRp (to see publications).

2. Connect to pg_replica (host port 5433):
```
psql -h localhost -p 5433 -U testuser -d testDB
```
Inside psql, check \dRs (to see subscriptions) and SELECT * FROM orders; to confirm replicated data.

# Cleaning Up
To stop and remove the Docker containers, networks, and persistent volumes:
```
docker compose down --volumes
```

