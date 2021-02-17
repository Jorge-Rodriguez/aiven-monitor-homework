import abc

from schema import Schema


class Runnable(abc.ABC):
    @abc.abstractmethod
    def run(self):
        pass

    CONFIG_SCHEMA: Schema
