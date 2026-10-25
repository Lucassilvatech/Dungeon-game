"""Integer gold with arbitrary precision in PostgreSQL; never floating point."""

from decimal import Decimal
from sqlalchemy import Numeric
from sqlalchemy.types import TypeDecorator


class Gold(TypeDecorator):
    impl = Numeric
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else Decimal(value)

    def process_result_value(self, value, dialect):
        return None if value is None else int(value)
