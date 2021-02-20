import json
import logging
from concurrent.futures import ThreadPoolExecutor

from confluent_kafka import Consumer
from psycopg2 import connect
from psycopg2.extras import DictCursor
from psycopg2.sql import SQL, Identifier
from schema import Schema

from url_monitor.interfaces import Runnable

logging.basicConfig(level=logging.INFO)


class Writer(Runnable):
    """Database writer runnable.

    Encapsulates the message listener and database persistence loop.

    Args:
        arguments (dict): The configuration dictionary as specified by `CONFIG_SCHEMA`.

    Attributes:
        consumer(confluent_kafka.Consumer): A Kafka Consumer object.
        topics (list): A list of Kafka topics to subscribe to.
        batch_size (int): The number of messages to read from the topic on each iteration
                          as specified by `prefetch_count` in the `kafka` configuration.
        db_conn (psycopg2.Connection): A postgresql connection object.

    """

    CONFIG_SCHEMA = Schema(
        {
            "kafka": {"connection": dict, "topics": [str], "prefetch_count": int},
            "postgres": dict,
        }
    )

    RUNNING = True  # Busy loop check value

    def __init__(self, arguments):
        self.logger = logging.getLogger("Writer")
        self.consumer = Consumer(**arguments["kafka"]["connection"])
        self.topics = arguments["kafka"]["topics"]
        self.batch_size = arguments["kafka"]["prefetch_count"]
        self.db_conn = connect(**arguments["postgres"])
        self.db_conn.set_session(autocommit=True)

        self.init_db()

    def __del__(self):
        """Ensure all connections are properly closed."""
        self.db_conn.close()
        self.consumer.close()

    def run(self):
        """Main execution loop.

        Each iteration of the loop consumes at most `batch_size` messages from
        the subscribed topics. A thread pool with as many workers as `batch_size`
        rounded to the next ten handles the high-latency database writes in parallel.

        """
        self.logger.info("Starting executor loop...")
        self.consumer.subscribe(self.topics)
        with ThreadPoolExecutor(
            max_workers=self.batch_size + 10 - (self.batch_size % 10)
        ) as executor:
            while self.RUNNING:
                message = self.consumer.poll()

                # Commit before processing for an "at most once" delivery strategy.
                self.consumer.commit(asynchronous=False)
                executor.submit(self.write, message)

    def write(self, message):
        """Database writer.

        Persists a message to the postgresql database.
        The message value is expected to be a JSON with the following keys:
            - "url"
            - "ts"
            - "status"
            - "latency"
            - "regex_match" (optional)

        Args:
            message (confluent_kafka.Message): The message as received from the Kafka topic.

        """
        if message.error() is None:
            self.logger.info("Writing message to database")
            payload = json.loads(message.value())

            with self.db_conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    SQL(  # See https://stackoverflow.com/a/6722460
                        """
                    WITH insert_row AS (
                        INSERT INTO {} (url)
                        SELECT %(url)s WHERE NOT EXISTS (
                            SELECT * FROM urls WHERE url = %(url)s
                        )
                        RETURNING *
                    )
                    SELECT * FROM insert_row
                    UNION
                    SELECT * FROM urls WHERE url = %(url)s
                    """
                    ).format(Identifier("urls")),
                    {"url": payload["url"]},
                )

                url_id = cursor.fetchone()["id"]

                cursor.execute(
                    SQL(
                        "INSERT INTO {} VALUES (%(url_id)s, %(ts)s, %(status)s, %(latency)s)"
                    ).format(Identifier("status")),
                    {
                        "url_id": url_id,
                        "ts": payload["check_time"],
                        "status": payload["status"],
                        "latency": payload["latency"],
                    },
                )

                if payload.get("regex_match"):
                    cursor.execute(
                        SQL(
                            "INSERT INTO {} VALUES (%(url_id)s, %(ts)s, %(match)s)"
                        ).format(Identifier("regex")),
                        {
                            "url_id": url_id,
                            "ts": payload["check_time"],
                            "match": payload["regex_match"],
                        },
                    )

        else:
            self.logger.warn("Received an error message. Ignoring.")

    def init_db(self):
        """Database initializer

        Creates the following tables in the database if they do not exist:
            - "urls": holds the monitored urls and their respective IDs.
            - "status": holds the URL checks' timestamp, status and latency.
            - "regex": holds the result of the regex searches for the URL checks.

        """
        with self.db_conn.cursor() as cursor:
            self.logger.info("Creating 'urls' table")
            cursor.execute(
                SQL(
                    """
                CREATE TABLE IF NOT EXISTS {} (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE
                )
                """
                ).format(Identifier("urls"))
            )

            self.logger.info("Creating 'status' table")
            cursor.execute(
                SQL(
                    """
                CREATE TABLE IF NOT EXISTS {} (
                    url_id INTEGER REFERENCES {} (id),
                    ts TIMESTAMP,
                    status INTEGER,
                    latency DECIMAL,
                    PRIMARY KEY (url_id, ts)
                )
                """
                ).format(Identifier("status"), Identifier("urls"))
            )

            self.logger.info("Creating 'regex' table")
            cursor.execute(
                SQL(
                    """
                CREATE TABLE IF NOT EXISTS {} (
                    url_id INTEGER REFERENCES {} (id),
                    ts TIMESTAMP,
                    regex_match BOOLEAN,
                    PRIMARY KEY (url_id, ts)
                )
                """
                ).format(Identifier("regex"), Identifier("urls"))
            )
