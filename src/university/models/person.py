"""
person.py — Abstract base class for all persons in the university system.
"""

from abc import ABC, abstractmethod


class Person(ABC):
    """
    Abstract base representing any person in the university.
    Subclasses must implement get_details().
    """

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name

    @abstractmethod
    def get_details(self) -> str:
        """Return a human-readable summary of this person."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, name={self.name!r})"
