
import psycopg2
import time
from datetime import date

MASTER_DB_PARAMS = {
    'host': 'localhost',
    'port': '5432',
    'database': 'testDB',
    'user': 'testuser',
    'password': 'testpassword'
}

REPLICA_DB_PARAMS = {
    'host': 'localhost',
    'port': '5433',
    'database': 'testDB',
    'user': 'testuser',
    'password': 'testpassword'
}

def connect_db(params):
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(**params)
        print(f"Successfully connected to DB at {params['host']}:{params['port']}")
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to DB at {params['host']}:{params['port']}: {e}")
        return None

def insert_sample_data(conn):
    """Inserts sample data into the orders table on the master."""
    try:
        cur = conn.cursor()
        print("\nInserting sample data into pg_master...")
        cur.execute(
            """
            INSERT INTO orders (product_name, quantity, order_date) VALUES
            ('Laptop', 2, %s),
            ('Mouse', 10, %s),
            ('Keyboard', 5, %s);
            """,
            (date(2023, 1, 15), date(2023, 1, 20), date(2023, 1, 25))
        )
        conn.commit()
        print("Sample data inserted successfully into pg_master.")
    except psycopg2.Error as e:
        print(f"Error inserting data into pg_master: {e}")
        conn.rollback()
    finally:
        if cur:
            cur.close()

def fetch_data(conn, db_name):
    """Fetches all data from the orders table."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, product_name, quantity, order_date FROM orders ORDER BY id;")
        rows = cur.fetchall()
        print(f"\n--- Data in {db_name} ---")
        if rows:
            for row in rows:
                print(f"ID: {row[0]}, Product: {row[1]}, Quantity: {row[2]}, Date: {row[3]}")
        else:
            print("No data found.")
        return rows
    except psycopg2.Error as e:
        print(f"Error fetching data from {db_name}: {e}")
        return []
    finally:
        if cur:
            cur.close()

def main():
    """Main function to orchestrate the process."""
    master_conn = None
    replica_conn = None

    try:
        # Give some time for Docker containers to fully initialize
        print("Waiting for PostgreSQL containers to be ready (approx. 45-60 seconds due to replica sleep)...")
        time.sleep(60) # Increased initial wait

        # Connect to master
        master_conn = connect_db(MASTER_DB_PARAMS)
        if not master_conn:
            print("Could not connect to master. Exiting.")
            return

        # Insert data into master
        insert_sample_data(master_conn)

        # Verify data on master
        master_rows = fetch_data(master_conn, "pg_master")

        # Give some time for logical replication to occur
        print("\nWaiting for replication to complete on pg_replica (approx. 10 seconds)...")
        time.sleep(10) # Replication is usually fast, but a small delay helps ensure sync

        # Connect to replica
        replica_conn = connect_db(REPLICA_DB_PARAMS)
        if not replica_conn:
            print("Could not connect to replica. Exiting.")
            return

        # Verify data on replica
        replica_rows = fetch_data(replica_conn, "pg_replica")

        # Compare data
        print("\n--- Replication Validation ---")
        if master_rows and master_rows == replica_rows:
            print("Validation successful: Data on pg_master and pg_replica are identical!")
        elif not master_rows and not replica_rows:
            print("No data found on either, but they are consistent (both empty).")
        else:
            print("Validation failed: Data on pg_master and pg_replica are different.")
            print("Master Rows:", master_rows)
            print("Replica Rows:", replica_rows)

    finally:
        # Close connections
        if master_conn:
            master_conn.close()
            print("Master connection closed.")
        if replica_conn:
            replica_conn.close()
            print("Replica connection closed.")

if __name__ == "__main__":
    main()

