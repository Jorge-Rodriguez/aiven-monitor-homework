"""
URL Monitor.

Usage:
    url_monitor.py monitor --config=<config_file>
    url_monitor.py writer --config=<config_file>

Options:
    -h --help                   Show this help message
    -c --config=<config_file>   Configuration file
"""
import json

import yaml
from docopt import docopt
from schema import SchemaError


def parse_configuration(config_file):
    with open(config_file) as fp:
        try:
            configuration = json.load(fp)
        except json.JSONDecodeError:
            fp.seek(0)
            try:
                configuration = yaml.safe_load(fp)
            except yaml.YAMLError:
                raise RuntimeError(
                    f"The configuration file {config_file} doesn't appear to be valid JSON or YAML"
                )
    return configuration


def main():
    arguments = docopt(__doc__)

    if arguments["monitor"]:
        from url_monitor.monitor import Monitor as Runnable
    else:
        from url_monitor.writer import Writer as Runnable

    try:
        Runnable(
            Runnable.CONFIG_SCHEMA.validate(parse_configuration(arguments["--config"]))
        ).run()
    except (RuntimeError, SchemaError) as e:
        exit(e)
