from enum import Enum


class JsonSerializableEnum(Enum):
    def to_json(self):
        return self._name_
