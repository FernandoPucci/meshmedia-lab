"""Isolated RGB332 codec used by the Issue #38 experiment."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from meshmedia_lab.media import CODEC_RGB332, ImageMetadata


MAX_RGB332_WIDTH = 64
MAX_RGB332_HEIGHT = 64

RgbPixel: TypeAlias = tuple[int, int, int]
RgbPixelMatrix: TypeAlias = Sequence[Sequence[RgbPixel]]

_RED_LEVELS = (0, 36, 73, 109, 146, 182, 219, 255)
_GREEN_LEVELS = _RED_LEVELS
_BLUE_LEVELS = (0, 85, 170, 255)


class Rgb332EncodingError(ValueError):
    """Raised when an RGB matrix cannot be encoded."""


class Rgb332DecodingError(ValueError):
    """Raised when an RGB332 representation cannot be decoded."""


@dataclass(frozen=True, slots=True)
class EncodedRgb332Image:
    """RGB332 bytes and the dimensions required to decode them."""

    width: int
    height: int
    data: bytes

    def __post_init__(self) -> None:
        _validate_dimensions(
            self.width,
            self.height,
            error_type=Rgb332EncodingError,
        )
        try:
            data = bytes(self.data)
        except (TypeError, ValueError) as error:
            raise Rgb332EncodingError("encoded data must be bytes-like") from error
        object.__setattr__(self, "data", data)
        expected_size = self.width * self.height
        if len(data) != expected_size:
            raise Rgb332EncodingError(
                f"encoded data has {len(data)} bytes; expected {expected_size}"
            )

    @property
    def metadata(self) -> ImageMetadata:
        """Return MM1 metadata without grayscale-only level semantics."""

        return ImageMetadata(
            width=self.width,
            height=self.height,
            levels=0,
            codec=CODEC_RGB332,
        )


class Rgb332Encoder:
    """Resize, quantize and pack an RGB image into one byte per pixel."""

    def __init__(self, width: int = 32, height: int = 32) -> None:
        _validate_dimensions(width, height, error_type=Rgb332EncodingError)
        self.width = width
        self.height = height

    def encode(self, pixels: RgbPixelMatrix) -> EncodedRgb332Image:
        source = self._validate_pixels(pixels)
        resized = self._resize(source)
        encoded = bytes(
            self._pack_pixel(pixel)
            for row in resized
            for pixel in row
        )
        return EncodedRgb332Image(
            width=self.width,
            height=self.height,
            data=encoded,
        )

    def _validate_pixels(
        self,
        pixels: RgbPixelMatrix,
    ) -> tuple[tuple[RgbPixel, ...], ...]:
        if not pixels or not pixels[0]:
            raise Rgb332EncodingError("pixel matrix cannot be empty")

        source_width = len(pixels[0])
        rows: list[tuple[RgbPixel, ...]] = []
        for row in pixels:
            if len(row) != source_width:
                raise Rgb332EncodingError("pixel rows must have the same width")

            normalized_row: list[RgbPixel] = []
            for pixel in row:
                try:
                    channels = tuple(pixel)
                except TypeError as error:
                    raise Rgb332EncodingError(
                        "pixels must contain exactly three channels"
                    ) from error
                if len(channels) != 3:
                    raise Rgb332EncodingError(
                        "pixels must contain exactly three channels"
                    )
                if any(
                    not isinstance(channel, int) or not 0 <= channel <= 255
                    for channel in channels
                ):
                    raise Rgb332EncodingError(
                        "channels must be integers in the range 0..255"
                    )
                normalized_row.append(
                    (channels[0], channels[1], channels[2])
                )
            rows.append(tuple(normalized_row))
        return tuple(rows)

    def _resize(
        self,
        pixels: tuple[tuple[RgbPixel, ...], ...],
    ) -> tuple[tuple[RgbPixel, ...], ...]:
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

    @staticmethod
    def _pack_pixel(pixel: RgbPixel) -> int:
        red, green, blue = pixel
        red_level = red * 8 // 256
        green_level = green * 8 // 256
        blue_level = blue * 4 // 256
        return (red_level << 5) | (green_level << 2) | blue_level


class Rgb332Decoder:
    """Unpack RGB332 bytes into reconstructed RGB pixels."""

    def decode(
        self,
        encoded: EncodedRgb332Image,
    ) -> tuple[tuple[RgbPixel, ...], ...]:
        if not isinstance(encoded, EncodedRgb332Image):
            raise Rgb332DecodingError("encoded image must be EncodedRgb332Image")

        pixels = tuple(
            (
                _RED_LEVELS[(value >> 5) & 0x07],
                _GREEN_LEVELS[(value >> 2) & 0x07],
                _BLUE_LEVELS[value & 0x03],
            )
            for value in encoded.data
        )
        return tuple(
            pixels[offset : offset + encoded.width]
            for offset in range(0, len(pixels), encoded.width)
        )


def _validate_dimensions(
    width: int,
    height: int,
    *,
    error_type: type[ValueError],
) -> None:
    if not 1 <= width <= MAX_RGB332_WIDTH:
        raise error_type(
            f"image width must be between 1 and {MAX_RGB332_WIDTH}"
        )
    if not 1 <= height <= MAX_RGB332_HEIGHT:
        raise error_type(
            f"image height must be between 1 and {MAX_RGB332_HEIGHT}"
        )


__all__ = [
    "EncodedRgb332Image",
    "MAX_RGB332_HEIGHT",
    "MAX_RGB332_WIDTH",
    "Rgb332Decoder",
    "Rgb332Encoder",
    "Rgb332EncodingError",
    "Rgb332DecodingError",
    "RgbPixel",
    "RgbPixelMatrix",
]
