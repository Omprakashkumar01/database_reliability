import psycopg2
import time

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

def connect_db(params, retries=30, delay=5, autocommit=False):
    for i in range(retries):
        try:
            conn = psycopg2.connect(**params)
            conn.autocommit = autocommit
            print(f"Successfully connected to DB at {params['host']}:{params['port']} (Attempt {i+1}/{retries}).")
            return conn
        except psycopg2.OperationalError as e:
            print(f"Connection to {params['host']}:{params['port']} failed. Retrying in {delay}s... ({e})")
            time.sleep(delay)
    print(f"Failed to connect to DB at {params['host']}:{params['port']} after {retries} attempts. Exiting.")
    return None

def ensure_db_and_table(db_params, is_master=False):
    """Ensures testDB and orders table exist for a given instance."""
    db_type = "master" if is_master else "replica"
    print(f"\nEnsuring database and table on {db_type}...")

    # Connect to 'postgres' database with autocommit for DB creation/drop
    params_initial = db_params.copy()
    params_initial['database'] = 'postgres'
    conn_initial = connect_db(params_initial, autocommit=True)
    if not conn_initial:
        return False

    try:
        cur_initial = conn_initial.cursor()
        # Terminate existing connections to testDB if any
        cur_initial.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_params['database']}' AND pid <> pg_backend_pid();
        """)
        cur_initial.execute(f"DROP DATABASE IF EXISTS {db_params['database']};")
        cur_initial.execute(f"CREATE DATABASE {db_params['database']};")
        print(f"Database '{db_params['database']}' ensured on {db_type}.")
    except psycopg2.Error as e:
        print(f"Error ensuring database on {db_type}: {e}")
        return False
    finally:
        if cur_initial:
            cur_initial.close()
        if conn_initial:
            conn_initial.close()

    # Connect to the specific testDB to create the table (non-autocommit)
    conn_testdb = connect_db(db_params, autocommit=False)
    if not conn_testdb:
        return False

    try:
        cur_testdb = conn_testdb.cursor()
        cur_testdb.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                order_date DATE NOT NULL
            );
        """)
        conn_testdb.commit()
        print(f"'orders' table ensured on {db_type}.")
        return True
    except psycopg2.Error as e:
        print(f"Error creating 'orders' table on {db_type}: {e}")
        conn_testdb.rollback()
        return False
    finally:
        if cur_testdb:
            cur_testdb.close()
        if conn_testdb:
            conn_testdb.close()

def check_wal_level_on_master():
    """Checks if wal_level on pg_master is 'logical'."""
    print("\nChecking wal_level on pg_master...")
    master_conn = None
    try:
        master_conn = connect_db(MASTER_DB_PARAMS, retries=5, delay=2, autocommit=True)
        if not master_conn:
            print("Could not connect to master to check wal_level.")
            return False
        cur = master_conn.cursor()
        cur.execute("SHOW wal_level;")
        wal_level = cur.fetchone()[0]
        print(f"pg_master wal_level: {wal_level}")
        return wal_level == 'logical'
    except psycopg2.Error as e:
        print(f"Error checking wal_level on pg_master: {e}")
        return False
    finally:
        if master_conn:
            master_conn.close()

def create_subscription(db_params):
    """Creates the logical replication subscription on the replica."""
    print("\nAttempting to create subscription on pg_replica...")
    conn_replica_testdb = connect_db(db_params, autocommit=True) # Must be autocommit
    if not conn_replica_testdb:
        return False

    try:
        cur = conn_replica_testdb.cursor()
        cur.execute("""
            CREATE SUBSCRIPTION my_subscription CONNECTION 'host=pg_master port=5432 user=testuser password=testpassword dbname=testDB' PUBLICATION my_publication;
        """)
        print("Subscription 'my_subscription' created successfully on pg_replica.")
        return True
    except psycopg2.Error as e:
        print(f"Error creating subscription on pg_replica: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn_replica_testdb:
            conn_replica_testdb.close()


def main():
    print("Starting database setup...")

    # Step 1: Wait for master and ensure its DB/table
    print("Ensuring pg_master is ready and configured...")
    if not ensure_db_and_table(MASTER_DB_PARAMS, is_master=True):
        print("Failed to set up pg_master. Exiting.")
        return

    # NEW: Ensure wal_level is logical on master before proceeding
    max_wal_level_checks = 15 # Increased attempts
    wal_level_check_delay = 5 # Increased delay
    for i in range(max_wal_level_checks):
        if check_wal_level_on_master():
            print("pg_master wal_level is 'logical'. Proceeding.")
            break
        else:
            print(f"pg_master wal_level is not 'logical' yet. Retrying in {wal_level_check_delay}s... (Attempt {i+1}/{max_wal_level_checks})")
            time.sleep(wal_level_check_delay)
    else:
        print("pg_master wal_level did not become 'logical' after multiple attempts. Aborting.")
        return

    # Step 2: Wait for replica and ensure its DB/table
    print("Ensuring pg_replica is ready and configured...")
    if not ensure_db_and_table(REPLICA_DB_PARAMS):
        print("Failed to set up pg_replica. Exiting.")
        return

    # Step 3: Create publication on master
    print("\nEnsuring publication on pg_master...")
    conn_master_pub = connect_db(MASTER_DB_PARAMS, autocommit=True)
    if not conn_master_pub:
        print("Failed to connect to master for publication setup.")
        return
    try:
        cur_master_pub = conn_master_pub.cursor()
        cur_master_pub.execute("DROP PUBLICATION IF EXISTS my_publication;")
        cur_master_pub.execute("CREATE PUBLICATION my_publication FOR TABLE orders;")
        print("Publication 'my_publication' ensured on pg_master.")
    except psycopg2.Error as e:
        print(f"Error ensuring publication on pg_master: {e}")
        return
    finally:
        if cur_master_pub:
            cur_master_pub.close()
        if conn_master_pub:
            conn_master_pub.close()

    # Step 4: Create subscription on replica
    # Add an explicit delay here as well, just in case
    print("Adding a short delay before creating subscription to ensure master stability...")
    time.sleep(10) # Added a slightly longer buffer here

    if create_subscription(REPLICA_DB_PARAMS):
        print("All database setup and replication configured successfully.")
    else:
        print("Failed to configure replication.")

if __name__ == "__main__":
    main()

