from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Goal:
    id: Optional[int]
    date: str
    title: str
    done: int

@dataclass
class Session:
    id: Optional[int]
    date: str
    start_ts: str
    end_ts: str
    minutes: int

@dataclass
class Distraction:
    id: Optional[int]
    date: str
    ts: str
    note: str