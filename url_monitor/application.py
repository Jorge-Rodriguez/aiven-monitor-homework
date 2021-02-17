"""
URL Monitor.

Usage:
    url_monitor monitor --config=<config_file>
    url_monitor writer --config=<config_file>

Options:
    -h --help                   Show this help message
    -c --config=<config_file>   Configuration file
"""
import json

import yaml
from docopt import docopt
from schema import SchemaError


def parse_configuration(config_file):
    """Loads the program's configuration from the provided configuration file.

    The configuration is expected to be JSON or YAML, if parsing of either
    format fails, a `RuntimeError` is raised.

    Args:
        config_file (str): The path to the configuration file.

    Returns:
        object: The parsed configuration as a python object.

    Raises:
        RuntimeError: If the contents of the configuration file are not valid JSON or YAML.

    """
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
    """Application entrypoint.

    Parses the command line arguments, loads the configuration file and validates said configuration.
    On success of the previous checks, starts the execution loop.

    """
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
