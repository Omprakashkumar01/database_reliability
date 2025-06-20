-- init_master.sql
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
CREATE PUBLICATION my_publication FOR TABLE orders;
SELECT 'Master database and publication initialized successfully.' AS status;
