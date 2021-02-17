import abc

from schema import Schema


class Runnable(abc.ABC):
    @abc.abstractmethod
    def run(self):
        pass

    # Expected configuration format for the Runnable instance
    CONFIG_SCHEMA: Schema
