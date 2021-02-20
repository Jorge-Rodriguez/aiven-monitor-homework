import json
import os
import time
from decimal import Decimal
from datetime import datetime

import psycopg2
from psycopg2.extras import DictCursor
from psycopg2.sql import SQL, Identifier, Literal


def target_id(cursor, target):
    query = cursor.mogrify(
        SQL("SELECT id FROM {} WHERE url = {}").format(
            Identifier("urls"), Literal(target["url"])
        )
    )
    cursor.execute(query)
    print(query)
    while not (result := cursor.fetchone()):
        print(result)
        time.sleep(1)
        cursor.execute(query)
    return result["id"]


def test_integration():
    with open(os.path.join(os.path.dirname(__file__), "config.json")) as fp:
        config = json.load(fp)
        with psycopg2.connect(**config["postgres"]) as conn:
            conn.set_session(autocommit=True)
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                for target in config["targets"]:
                    url_id = target_id(cursor, target)
                    cursor.execute(
                        "SELECT * FROM status WHERE url_id = %s LIMIT 1", (url_id,)
                    )
                    status = cursor.fetchone()

                    assert isinstance(status["ts"], datetime)
                    assert isinstance(status["status"], int)
                    assert isinstance(status["latency"], Decimal)

                    if target.get("regex"):
                        cursor.execute("SELECT * FROM regex WHERE url_id = %s LIMIT 1", (url_id,))
                        regex = cursor.fetchone()

                        assert isinstance(regex["ts"], datetime)
                        assert isinstance(regex["regex_match"], bool)
