from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    name: str
    age: int
    birthdate: datetime
