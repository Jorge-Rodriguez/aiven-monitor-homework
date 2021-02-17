import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from time import sleep

from confluent_kafka import KafkaException, Producer
from requests import get
from requests.exceptions import RequestException, Timeout
from schema import And, Optional, Schema, Use

from url_monitor.interfaces import Runnable


class JSONDatetimeEncoder(json.JSONEncoder):
    """
    JSON encoder with datetime serialization capabilities.
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(JSONDatetimeEncoder, self).default(obj)


class Monitor(Runnable):

    CONFIG_SCHEMA = Schema(
        {
            "kafka": {"connection": dict, "topic": str},
            "targets": [
                {
                    "url": str,
                    "frequency": And(
                        Use(int), lambda n: n > 0, error="frequency can't be < 1"
                    ),
                    Optional("regex"): str,
                }
            ],
        }
    )

    RUNNING = True  # Busy loop check value

    def __init__(self, arguments):
        self.logger = logging.getLogger("Monitor")
        self.config = arguments["targets"]
        self.producer = Producer(arguments["kafka"]["connection"])
        self.topic = arguments["kafka"]["topic"]

    def run(self):
        with ThreadPoolExecutor(
            max_workers=len(self.config) + 10 - (len(self.config) % 10)
        ) as executor:
            for target in self.config:
                executor.submit(self.monitor, target)

    def monitor(self, target):
        while self.RUNNING:
            check_time = datetime.now()
            next_check = check_time + timedelta(seconds=target["frequency"])

            try:
                self.produce(
                    get(target["url"], timeout=target["frequency"] - 0.5),
                    target.get("regex"),
                    check_time,
                )
            except Timeout:
                self.logger.warning("Check for %s timed out", target["url"])
            except RequestException as e:
                self.logger.error(e)

            # Busy loop until next check_time
            while datetime.now() < next_check:
                sleep(1)

    def produce(self, response, regex, ts):
        def log_produced(err, msg):
            if err is not None:
                self.logger.warning(
                    "Failed to deliver message: %s.  Error: %s", msg, err
                )
            else:
                self.logger.info("Produced message: %s", msg)

        payload = {
            "url": response.url,
            "latency": response.elapsed,
            "status": response.status_code,
            "check_time": ts,
        }

        if regex:
            payload["regex_match"] = bool(re.search(regex, response.text))

        try:
            self.producer.produce(
                self.topic,
                value=json.dumps(payload, cls=JSONDatetimeEncoder),
                callback=log_produced,
            )
            self.producer.poll(1)
        except KafkaException as e:
            self.logger.error(
                "An error occurred while producing a message: %s", e.args[0].reason
            )
