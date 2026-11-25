"""Deterministic grayscale fixtures used by the Issue #24 experiments."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised without the local extra
    Image = None

from .config import fixture_seed

GrayPixels: TypeAlias = tuple[tuple[int, ...], ...]

GRAY_LEVELS = 16
GRAY_PALETTE: tuple[int, ...] = tuple(
    round(index * 255 / (GRAY_LEVELS - 1))
    for index in range(GRAY_LEVELS)
)


def _resampling_filter(name: str):
    if Image is None:
        raise RuntimeError("Pillow is required for image fixtures")
    resampling = getattr(Image, "Resampling", Image)
    return getattr(resampling, name)


@dataclass(frozen=True, slots=True)
class Fixture:
    """One named, resolution-specific reference image."""

    fixture_id: str
    description: str
    width: int
    height: int
    seed: int
    pixels: GrayPixels
    source_path: str | None = None


def _palette(index: int) -> int:
    return GRAY_PALETTE[index % len(GRAY_PALETTE)]


def _blank(width: int, height: int, value: int) -> list[list[int]]:
    return [[value for _ in range(width)] for _ in range(height)]


def _fill_rectangle(
    pixels: list[list[int]],
    left: int,
    top: int,
    right: int,
    bottom: int,
    value: int,
) -> None:
    height = len(pixels)
    width = len(pixels[0])
    for y in range(max(0, top), min(height, bottom)):
        for x in range(max(0, left), min(width, right)):
            pixels[y][x] = value


def _geometry_fixture(width: int, height: int, seed: int) -> GrayPixels:
    rng = random.Random(seed)
    pixels = _blank(width, height, _palette(1))
    line = max(1, min(width, height) // 32)
    dark = _palette(rng.choice((0, 2, 3)))
    light = _palette(rng.choice((12, 14, 15)))

    for offset in range(line):
        for x in range(width):
            pixels[offset][x] = light
            pixels[height - 1 - offset][x] = light
        for y in range(height):
            pixels[y][offset] = light
            pixels[y][width - 1 - offset] = light

    verticals = (width // 4, width // 2, (3 * width) // 4)
    horizontals = (height // 4, height // 2, (3 * height) // 4)
    for x in verticals:
        for offset in range(line):
            if 0 <= x + offset < width:
                for y in range(height):
                    pixels[y][x + offset] = dark
    for y in horizontals:
        for offset in range(line):
            if 0 <= y + offset < height:
                for x in range(width):
                    pixels[y + offset][x] = dark

    block_size = max(2, min(width, height) // 8)
    block_values = (_palette(4), _palette(8), _palette(11), _palette(15))
    for row in range(2):
        for column in range(2):
            left = width // 8 + column * (width // 2)
            top = height // 8 + row * (height // 2)
            value = rng.choice(block_values)
            _fill_rectangle(
                pixels,
                left,
                top,
                left + block_size,
                top + block_size,
                value,
            )

    diagonal = _palette(rng.choice((5, 7, 10)))
    for coordinate in range(min(width, height)):
        for offset in range(line):
            x = coordinate + offset
            y = coordinate
            if x < width and y < height:
                pixels[y][x] = diagonal
    return tuple(tuple(row) for row in pixels)


def _gradient_fixture(width: int, height: int, seed: int) -> GrayPixels:
    phase = seed % GRAY_LEVELS
    pixels: list[tuple[int, ...]] = []
    for y in range(height):
        row: list[int] = []
        vertical = (y * (GRAY_LEVELS - 1)) // max(1, height - 1)
        for x in range(width):
            horizontal = (x * (GRAY_LEVELS - 1)) // max(1, width - 1)
            diagonal = ((x + y + phase) * 3) // max(1, width + height)
            row.append(_palette((horizontal + vertical + diagonal) // 2))
        pixels.append(tuple(row))
    return tuple(pixels)


def _quantize_to_palette(value: int) -> int:
    level = round(value * (GRAY_LEVELS - 1) / 255)
    return _palette(level)


def _cat_fixture(
    width: int,
    height: int,
    source_path: Path,
) -> GrayPixels:
    if Image is None:
        raise RuntimeError(
            "Pillow is required to generate TEST-03 from test-images/cat.jpeg"
        )
    with Image.open(source_path) as source:
        grayscale = source.convert("L").resize(
            (width, height),
            _resampling_filter("BILINEAR"),
        )
        values = tuple(grayscale.getdata())
    return tuple(
        tuple(
            _quantize_to_palette(values[offset + x])
            for x in range(width)
        )
        for offset in range(0, width * height, width)
    )


def build_fixture(
    fixture_id: str,
    width: int,
    height: int,
    *,
    source_root: Path = Path("."),
) -> Fixture:
    """Build one deterministic fixture at the requested resolution."""

    if width <= 0 or height <= 0:
        raise ValueError("fixture dimensions must be positive")
    seed = fixture_seed(fixture_id)
    if fixture_id == "TEST-01":
        pixels = _geometry_fixture(width, height, seed)
        description = "geometria, linhas, bordas e blocos"
        source_path = None
    elif fixture_id == "TEST-02":
        pixels = _gradient_fixture(width, height, seed)
        description = "gradientes e variacoes tonais"
        source_path = None
    elif fixture_id == "TEST-03":
        path = source_root / "test-images" / "cat.jpeg"
        if not path.exists():
            raise FileNotFoundError(path)
        pixels = _cat_fixture(width, height, path)
        description = "detalhes e padroes da imagem de teste existente"
        source_path = str(path)
    else:
        raise ValueError(f"unknown fixture: {fixture_id}")

    return Fixture(
        fixture_id=fixture_id,
        description=description,
        width=width,
        height=height,
        seed=seed,
        pixels=pixels,
        source_path=source_path,
    )


def save_fixture_png(fixture: Fixture, path: Path) -> None:
    """Save a fixture without changing its native pixel values."""

    if Image is None:
        raise RuntimeError("Pillow is required to save reference fixtures")
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("L", (fixture.width, fixture.height))
    image.putdata([pixel for row in fixture.pixels for pixel in row])
    image.save(path)


def save_gray_pixels(pixels: GrayPixels, path: Path) -> None:
    """Save a reconstructed grayscale matrix without interpolation."""

    if Image is None:
        raise RuntimeError("Pillow is required to save reconstructed images")
    if not pixels or not pixels[0]:
        raise ValueError("pixel matrix cannot be empty")
    width = len(pixels[0])
    if any(len(row) != width for row in pixels):
        raise ValueError("pixel rows must have the same width")
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("L", (width, len(pixels)))
    image.putdata([pixel for row in pixels for pixel in row])
    image.save(path)


def generate_reference_images(
    output_directory: Path,
    *,
    source_root: Path = Path("."),
) -> tuple[dict[str, object], ...]:
    """Generate all reference images and return their manifest entries."""

    entries: list[dict[str, object]] = []
    for fixture_id in ("TEST-01", "TEST-02", "TEST-03"):
        for width, height in ((32, 32), (64, 64), (128, 128)):
            fixture = build_fixture(
                fixture_id,
                width,
                height,
                source_root=source_root,
            )
            path = output_directory / fixture_id / f"{width}x{height}.png"
            save_fixture_png(fixture, path)
            entries.append(
                {
                    "fixture_id": fixture.fixture_id,
                    "description": fixture.description,
                    "resolution": f"{width}x{height}",
                    "width": width,
                    "height": height,
                    "seed": fixture.seed,
                    "source_path": fixture.source_path,
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )

    manifest_path = output_directory / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"fixtures": entries}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tuple(entries)
