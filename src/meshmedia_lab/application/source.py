"""Input boundaries for image data."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeAlias

PixelMatrix: TypeAlias = Sequence[Sequence[int]]


class ImageSource(Protocol):
    """Source of grayscale pixel matrices."""

    def read(self) -> PixelMatrix:
        """Return the next image as rows of 8-bit grayscale pixels."""


@dataclass(frozen=True, slots=True)
class MemoryImageSource:
    """Simple source used by the local MVP and its tests."""

    pixels: PixelMatrix

    def read(self) -> PixelMatrix:
        return self.pixels
