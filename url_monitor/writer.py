import json
import logging
from concurrent.futures import ThreadPoolExecutor

from confluent_kafka import Consumer, KafkaError
from psycopg2 import connect
from psycopg2.extras import DictCursor
from schema import Schema

from url_monitor.interfaces import Runnable


class Writer(Runnable):

    CONFIG_SCHEMA = Schema(
        {
            "kafka": {"connection": dict, "topics": [str], "prefetch_count": int},
            "postgres": dict,
        }
    )

    RUNNING = True  # Busy loop check value

    def __init__(self, arguments):
        self.logger = logging.getLogger("Writer")
        self.consumer = Consumer(arguments["kafka"]["connection"])
        self.topics = arguments["kafka"]["topics"]
        self.batch_size = arguments["kafka"]["prefetch_count"]
        self.db_conn = connect(*arguments["postgres"])

        self.init_db()

    def __del__(self):
        self.db_conn.close()
        self.consumer.close()

    def run(self):
        self.consumer.subscribe(self.topics)
        while self.RUNNING:
            try:
                messages = self.consumer.consume(num_messages=self.batch_size)
            except KafkaError as e:
                self.logger.error(
                    "An error occurred while consuming messages: %s", e.reason
                )
                continue

            # Commit before processing for an "at most once" delivery strategy.
            self.consumer.commit(asynchronous=False)
            with ThreadPoolExecutor(
                max_workers=self.batch_size + 10 - (self.batch_size % 10)
            ) as executor:
                for message in messages:
                    executor.submit(self.write, message)

    def write(self, message):
        if message.error() is None:
            self.logger.info("Writing message to database")
            payload = json.loads(message.value())

            with self.db_conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    """
                    WITH insert_row AS (
                        INSERT INTO monitored_urls (url)
                        SELECT %(url)s WHERE NOT EXISTS (
                            SELECT * FROM monitored_urls WHERE url = %(url)s
                        )
                        RETURNING *
                    )
                    SELECT * FROM insert_row
                    UNION
                    SELECT * FROM monitored_urls WHERE url = %(url)s
                    """,
                    {"url": payload["url"]},
                )

                url_id = cursor.fetch_one()["id"]

                cursor.execute(
                    "INSERT INTO status VALUES (%(url_id)s, %(ts)s, %(status)s, %(latency)s)",
                    {
                        "url_id": url_id,
                        "ts": payload["check_time"],
                        "status": payload["status"],
                        "latency": payload["latency"],
                    },
                )

                if payload.get("regex_match"):
                    cursor.execute(
                        "INSERT INTO regex_check VALUES (%(url_id)s, %(ts)s, %(match)s)",
                        {
                            "url_id": url_id,
                            "ts": payload["check_time"],
                            "match": payload["regex_match"],
                        },
                    )
        else:
            self.logger.warn("Received an error message. Ignoring.")

    def init_db(self):
        with self.db_conn.cursor() as cursor:
            self.logger.info("Creating 'monitored_urls' table")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS monitored_urls (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE
                )
                """
            )

            self.logger.info("Creating 'status' table")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS status (
                    url_id INTEGER REFERENCES monitored_urls (id),
                    timestamp TIMESTAMP,
                    status INTEGER,
                    latency DECIMAL,
                    PRIMARY KEY (url_id, timestamp)
                )
                """
            )

            self.logger.info("Creating 'regex_check' table")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS regex_check (
                    url_id INTEGER REFERENCES monitored_urls (id),
                    timestamp TIMESTAMP,
                    regex_match BOOLEAN,
                    PRIMARY KEY (url_id, timestamp)
                )
                """
            )
