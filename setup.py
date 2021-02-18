from setuptools import find_packages, setup

setup(
    name="url_monitor",
    author="Jorge Rodriguez",
    description="Utility to check website availability",
    packages=find_packages(),
    install_requires=[
        "confluent-kafka",
        "docopt",
        "psycopg2-binary",
        "PyYAML",
        "schema",
        "requests",
    ],
)
