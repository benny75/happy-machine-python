import psycopg2
import psycopg2.extras

# Establish a connection to the source database
source_conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="password",
    host="localhost",
    port="5432"
)

# Establish a connection to the target database
target_conn = psycopg2.connect(
    dbname="postgres",
    host="localhost",
    port="5436"
)

# Define the fetch size
fetch_size = 1000

try:
    with source_conn, target_conn:
        with source_conn.cursor('source_cur',
                                cursor_factory=psycopg2.extras.DictCursor) as source_cur, target_conn.cursor() as target_cur:

            # Set the fetch size for the source cursor
            source_cur.itersize = fetch_size

            # Execute the SELECT query on the source database
            source_cur.execute("SELECT * FROM stick;")

            while True:
                # Fetch the next set of rows from the source database
                rows = source_cur.fetchmany(fetch_size)

                if not rows:
                    break

                # Define the INSERT query for the target database
                insert_query = "INSERT INTO stick VALUES %s"

                # Execute the INSERT query on the target database
                psycopg2.extras.execute_values(target_cur, insert_query, rows, template=None, page_size=fetch_size)
                print(f"insert success")


except psycopg2.Error as e:
    print(f"An error occurred: {e}")

finally:
    # Close the database connections
    source_conn.close()
    target_conn.close()
