"""Decoder for the initial packed grayscale representation."""

from meshmedia_lab.codec.encoder import EncodedImage


class ImageDecodingError(ValueError):
    """Raised when encoded image data cannot be decoded."""


class ImageDecoder:
    """Unpack quantized grayscale pixels into an image matrix."""

    def decode(self, encoded: EncodedImage) -> tuple[tuple[int, ...], ...]:
        values = self._unpack(encoded)
        scale = 255 / (encoded.levels - 1)
        pixels = tuple(round(value * scale) for value in values)
        return tuple(
            pixels[offset : offset + encoded.width]
            for offset in range(0, len(pixels), encoded.width)
        )

    def _unpack(self, encoded: EncodedImage) -> tuple[int, ...]:
        bits_per_pixel = encoded.bits_per_pixel
        values: list[int] = []
        accumulator = 0
        bits = 0

        for byte in encoded.data:
            accumulator = (accumulator << 8) | byte
            bits += 8
            while bits >= bits_per_pixel and len(values) < encoded.width * encoded.height:
                bits -= bits_per_pixel
                values.append((accumulator >> bits) & (encoded.levels - 1))

        expected_pixels = encoded.width * encoded.height
        if len(values) != expected_pixels:
            raise ImageDecodingError("encoded data does not contain enough pixels")
        return tuple(values)
