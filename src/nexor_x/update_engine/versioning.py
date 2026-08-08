from __future__ import annotations

from dataclasses import dataclass
import re


class VersionError(ValueError):
    pass


@dataclass(frozen=True, order=True, slots=True)
class Version:
    major: int
    minor: int
    patch: int

    _PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = cls._PATTERN.fullmatch(value.strip())
        if match is None:
            raise VersionError(f"Invalid semantic version: {value!r}")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_next_after(self, previous: "Version") -> bool:
        if self <= previous:
            return False
        if self.major == previous.major and self.minor == previous.minor:
            return self.patch == previous.patch + 1
        if self.major == previous.major:
            return self.minor == previous.minor + 1 and self.patch == 0
        return self.major == previous.major + 1 and self.minor == 0 and self.patch == 0
