import abc
from typing import Dict, Any


class AutoJson(abc.ABC):
    @abc.abstractmethod
    def jsonify(self) -> Dict[str, Any]:
        raise NotImplementedError()


class Slots(AutoJson):
    """
    Class that implements the jsonify method by looking into the __slots__ attribute.
    Make sure all __slots__ fields are (auto)json-serializable.
    """
    def jsonify(self) -> Dict[str, Any]:
        d = {}
        for k in self.__slots__:
            attr = getattr(self, k)
            if issubclass(type(attr), AutoJson):
                # Recursively jsonify AutoJson attributes
                d[k] = attr.jsonify()
            else:
                d[k] = attr
        return d
