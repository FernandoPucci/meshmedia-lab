"""Pillow integration kept at the local application boundary."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from PIL.Image import Image as PillowImage

PixelMatrix = tuple[tuple[int, ...], ...]
RgbPixelMatrix = tuple[tuple[tuple[int, int, int], ...], ...]


def load_grayscale_pixels(path: str | Path) -> PixelMatrix:
    """Load any Pillow-supported image as an 8-bit grayscale matrix."""

    with Image.open(path) as source:
        grayscale = source.convert("L")
        width, height = grayscale.size
        return tuple(
            tuple(int(grayscale.getpixel((x, y))) for x in range(width))
            for y in range(height)
        )


def load_rgb_pixels(path: str | Path) -> RgbPixelMatrix:
    """Load any Pillow-supported image as an 8-bit RGB matrix."""

    with Image.open(path) as source:
        rgb = source.convert("RGB")
        width, height = rgb.size
        return tuple(
            tuple(
                tuple(int(channel) for channel in rgb.getpixel((x, y)))
                for x in range(width)
            )
            for y in range(height)
        )


def pixels_to_image(pixels: PixelMatrix) -> PillowImage:
    """Convert a grayscale matrix into a Pillow image."""

    if not pixels or not pixels[0]:
        raise ValueError("pixel matrix cannot be empty")
    width = len(pixels[0])
    if any(len(row) != width for row in pixels):
        raise ValueError("pixel rows must have the same width")
    image = Image.new("L", (width, len(pixels)))
    image.putdata([pixel for row in pixels for pixel in row])
    return image


def rgb_pixels_to_image(pixels: RgbPixelMatrix) -> PillowImage:
    """Convert an RGB matrix into a Pillow image."""

    if not pixels or not pixels[0]:
        raise ValueError("pixel matrix cannot be empty")
    width = len(pixels[0])
    if any(len(row) != width for row in pixels):
        raise ValueError("pixel rows must have the same width")
    image = Image.new("RGB", (width, len(pixels)))
    image.putdata([pixel for row in pixels for pixel in row])
    return image


def save_pixels(pixels: PixelMatrix, path: str | Path) -> None:
    """Save a grayscale matrix using the output format selected by Pillow."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = pixels_to_image(pixels)
    image.save(output)


def save_rgb_pixels(pixels: RgbPixelMatrix, path: str | Path) -> None:
    """Save an RGB matrix using the output format selected by Pillow."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = rgb_pixels_to_image(pixels)
    image.save(output)


def show_pixels(pixels: PixelMatrix, title: str) -> None:
    """Open the reconstructed image in the system image viewer."""

    pixels_to_image(pixels).show(title=title)


def show_rgb_pixels(pixels: RgbPixelMatrix, title: str) -> None:
    """Open a reconstructed RGB image in the system image viewer."""

    rgb_pixels_to_image(pixels).show(title=title)
