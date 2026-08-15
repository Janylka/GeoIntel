from enum import Enum


class Scope(str, Enum):  # noqa: UP042 -- str mixin required, frozen contract
    COUNTRY = "country"
    OBLAST = "oblast"
    DISTRICT = "district"
    FIELD = "field"

    def is_finer_than(self, other: "Scope") -> bool:
        """Checks if this scope is geographically smaller than another."""
        order = [Scope.COUNTRY, Scope.OBLAST, Scope.DISTRICT, Scope.FIELD]
        try:
            return order.index(self) > order.index(other)
        except ValueError:
            return False
