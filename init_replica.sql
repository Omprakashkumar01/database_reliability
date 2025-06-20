-- init_replica.sql
\c postgres;
DROP DATABASE IF EXISTS testDB;
CREATE DATABASE testDB;
\c testDB;
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    order_date DATE NOT NULL
);

-- IMPORTANT: Add a significant delay to ensure master is fully ready and its wal_level is effective
SELECT 'Waiting for master to be fully ready before creating subscription...' AS status;
SELECT pg_sleep(30); -- Increased sleep time

CREATE SUBSCRIPTION my_subscription CONNECTION 'host=pg_master port=5432 user=testuser password=testpassword dbname=testDB' PUBLICATION my_publication;
SELECT 'Replica database and subscription initialized successfully.' AS status;

