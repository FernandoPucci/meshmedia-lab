"""Initial grayscale image encoder for the local MVP."""

from collections.abc import Sequence
from dataclasses import dataclass

from meshmedia_lab.media import ImageMetadata

class ImageEncodingError(ValueError):
    """Raised when a pixel matrix cannot be encoded."""


@dataclass(frozen=True, slots=True)
class EncodedImage:
    """Binary image representation with the metadata needed to decode it."""

    width: int
    height: int
    levels: int
    data: bytes

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ImageEncodingError("image dimensions must be positive")
        if self.levels not in (2, 4, 8, 16, 256):
            raise ImageEncodingError("levels must be 2, 4, 8, 16 or 256")
        expected_size = (self.width * self.height * self.bits_per_pixel + 7) // 8
        if len(self.data) != expected_size:
            raise ImageEncodingError(
                f"encoded data has {len(self.data)} bytes; expected {expected_size}"
            )

    @property
    def bits_per_pixel(self) -> int:
        return self.levels.bit_length() - 1

    @property
    def metadata(self) -> ImageMetadata:
        return ImageMetadata(
            width=self.width,
            height=self.height,
            levels=self.levels,
        )


class ImageEncoder:
    """Resize, quantize and pack an 8-bit grayscale image."""

    def __init__(self, width: int = 32, height: int = 32, levels: int = 16) -> None:
        if width <= 0 or height <= 0:
            raise ImageEncodingError("target dimensions must be positive")
        if levels not in (2, 4, 8, 16, 256):
            raise ImageEncodingError("levels must be 2, 4, 8, 16 or 256")
        self.width = width
        self.height = height
        self.levels = levels

    def encode(self, pixels: Sequence[Sequence[int]]) -> EncodedImage:
        source = self._validate_pixels(pixels)
        resized = self._resize(source)
        values = [self._quantize(pixel) for row in resized for pixel in row]
        return EncodedImage(
            width=self.width,
            height=self.height,
            levels=self.levels,
            data=self._pack(values),
        )

    def _validate_pixels(
        self, pixels: Sequence[Sequence[int]]
    ) -> tuple[tuple[int, ...], ...]:
        if not pixels or not pixels[0]:
            raise ImageEncodingError("pixel matrix cannot be empty")

        width = len(pixels[0])
        rows: list[tuple[int, ...]] = []
        for row in pixels:
            if len(row) != width:
                raise ImageEncodingError("pixel rows must have the same width")
            if any(not isinstance(pixel, int) or not 0 <= pixel <= 255 for pixel in row):
                raise ImageEncodingError("pixels must be integers in the range 0..255")
            rows.append(tuple(row))
        return tuple(rows)

    def _resize(self, pixels: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
        source_height = len(pixels)
        source_width = len(pixels[0])
        return tuple(
            tuple(
                pixels[
                    min(source_height - 1, y * source_height // self.height)
                ][min(source_width - 1, x * source_width // self.width)]
                for x in range(self.width)
            )
            for y in range(self.height)
        )

    def _quantize(self, pixel: int) -> int:
        return min(self.levels - 1, pixel * self.levels // 256)

    def _pack(self, values: list[int]) -> bytes:
        bits_per_pixel = self.levels.bit_length() - 1
        output = bytearray()
        accumulator = 0
        bits = 0

        for value in values:
            accumulator = (accumulator << bits_per_pixel) | value
            bits += bits_per_pixel
            if bits >= 8:
                bits -= 8
                output.append((accumulator >> bits) & 0xFF)

        if bits:
            output.append((accumulator << (8 - bits)) & 0xFF)
        return bytes(output)
