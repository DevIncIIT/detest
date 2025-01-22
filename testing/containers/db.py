import docker
import time
import psycopg2

client = docker.from_env()

CONTAINER_NAME = "postgres_multidb_container"
PORT = 6969


def create_db_container(no_of_databases: int) -> list[str] | None:
    """
    Creates a PostgreSQL Docker container with the specified number of databases.

    Args:
        no_of_databases (int): Number of databases to create.

    Returns:
        list[str] | None: List of database names if successful, None otherwise.
    """
    # containers = client.containers.list()
    # if CONTAINER_NAME in [container.name for container in containers]:
    #     print(f"Container {CONTAINER_NAME} already exists.")
    #     drop_db_container()
    #     time.sleep(5)

    try:
        # Pull the PostgreSQL Docker image
        client.images.pull("postgres:latest")

        # Define environment variables
        env_vars = {"POSTGRES_USER": "admin", "POSTGRES_PASSWORD": "password"}

        # Create and start the container
        _ = client.containers.run(
            "postgres:latest",
            name=CONTAINER_NAME,
            environment=env_vars,
            ports={"5432/tcp": PORT},
            detach=True,
        )

        while True:
            try:
                connection = psycopg2.connect(
                    host="localhost", port=PORT, user="admin", password="password"
                )
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
        connection.autocommit = True
        cursor = connection.cursor()

        db_names = []
        for i in range(no_of_databases):
            db_name = f"database_{i + 1}"
            cursor.execute(f"CREATE DATABASE {db_name};")
            db_names.append(db_name)

        cursor.close()
        connection.close()

        return [f'postgresql://admin:password@0.0.0.0:{PORT}/{dbn}' for dbn in db_names]

    except Exception as e:
        print(f"Error: {e}")
        return None


def drop_db_container() -> bool:
    """
    Stops and removes the PostgreSQL Docker container.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.stop()
        container.remove()
        return True
    # except docker.errors.NotFound:
    #     print(f"Container {CONTAINER_NAME} not found.")
    #     return False
    except Exception as e:
        print(f"Error: {e}")
        return False
