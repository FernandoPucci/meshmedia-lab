"""Compare the isolated RGB332 experiment with the grayscale baseline."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import TypeAlias, TypeVar

try:
    from PIL import Image
except ImportError:  # pragma: no cover - depends on the local extra
    Image = None

from apps.local.common import parse_resolution
from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import ImageEncoder
from meshmedia_lab.codec.rgb332 import Rgb332Decoder, Rgb332Encoder


GrayPixels: TypeAlias = tuple[tuple[int, ...], ...]
RgbPixels: TypeAlias = tuple[tuple[tuple[int, int, int], ...], ...]
Pixel = TypeVar("Pixel")


def _resolution_argument(value: str) -> tuple[int, int]:
    try:
        resolution = parse_resolution(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    if resolution not in ((32, 32), (64, 64)):
        raise argparse.ArgumentTypeError(
            "RGB332 experiment resolutions must be 32x32 or 64x64"
        )
    return resolution


def _load_pixels(path: Path) -> tuple[RgbPixels, GrayPixels]:
    if Image is None:
        raise RuntimeError("Pillow is required for the visual experiment")

    with Image.open(path) as source:
        rgb = source.convert("RGB")
        grayscale = source.convert("L")
        rgb_values = tuple(rgb.getdata())
        grayscale_values = tuple(grayscale.getdata())
        width, height = source.size

    rgb_pixels = tuple(
        tuple(
            rgb_values[offset + x]
            for x in range(width)
        )
        for offset in range(0, width * height, width)
    )
    gray_pixels = tuple(
        tuple(
            int(grayscale_values[offset + x])
            for x in range(width)
        )
        for offset in range(0, width * height, width)
    )
    return rgb_pixels, gray_pixels


def _resize(
    pixels: Sequence[Sequence[Pixel]],
    width: int,
    height: int,
) -> tuple[tuple[Pixel, ...], ...]:
    source_height = len(pixels)
    source_width = len(pixels[0])
    return tuple(
        tuple(
            pixels[
                min(source_height - 1, y * source_height // height)
            ][min(source_width - 1, x * source_width // width)]
            for x in range(width)
        )
        for y in range(height)
    )


def _quality_gray(reference: GrayPixels, actual: GrayPixels) -> dict[str, float | None]:
    squared_error = 0
    absolute_error = 0
    samples = 0
    for reference_row, actual_row in zip(reference, actual):
        for reference_pixel, actual_pixel in zip(reference_row, actual_row):
            difference = reference_pixel - actual_pixel
            squared_error += difference * difference
            absolute_error += abs(difference)
            samples += 1
    return _quality_result(absolute_error, squared_error, samples)


def _quality_rgb(reference: RgbPixels, actual: RgbPixels) -> dict[str, float | None]:
    squared_error = 0
    absolute_error = 0
    samples = 0
    for reference_row, actual_row in zip(reference, actual):
        for reference_pixel, actual_pixel in zip(reference_row, actual_row):
            for reference_channel, actual_channel in zip(
                reference_pixel,
                actual_pixel,
            ):
                difference = reference_channel - actual_channel
                squared_error += difference * difference
                absolute_error += abs(difference)
                samples += 1
    return _quality_result(absolute_error, squared_error, samples)


def _quality_result(
    absolute_error: int,
    squared_error: int,
    samples: int,
) -> dict[str, float | None]:
    mean_absolute_error = absolute_error / samples
    mean_squared_error = squared_error / samples
    psnr = None
    if mean_squared_error:
        psnr = 10 * math.log10((255 * 255) / mean_squared_error)
    return {
        "mae": mean_absolute_error,
        "mse": mean_squared_error,
        "psnr_db": psnr,
    }


def _mm1_cost(encoded_bytes: int, payload_limit: int) -> dict[str, int]:
    fragment_count = max(
        1,
        (encoded_bytes + payload_limit - 1) // payload_limit,
    )
    header_bytes = fragment_count * 19
    crc_bytes = fragment_count * 2
    overhead_bytes = header_bytes + crc_bytes
    return {
        "encoded_bytes": encoded_bytes,
        "fragment_count": fragment_count,
        "header_bytes": header_bytes,
        "crc_bytes": crc_bytes,
        "overhead_bytes": overhead_bytes,
        "wire_bytes": encoded_bytes + overhead_bytes,
    }


def _save_rgb(pixels: RgbPixels, path: Path) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required for the visual experiment")
    image = Image.new("RGB", (len(pixels[0]), len(pixels)))
    image.putdata([pixel for row in pixels for pixel in row])
    image.save(path)


def _save_gray(pixels: GrayPixels, path: Path) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required for the visual experiment")
    image = Image.new("L", (len(pixels[0]), len(pixels)))
    image.putdata([pixel for row in pixels for pixel in row])
    image.save(path)


def _save_comparison(
    reference: RgbPixels,
    rgb332: RgbPixels,
    grayscale: GrayPixels,
    path: Path,
) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required for the visual experiment")

    width = len(reference[0])
    height = len(reference)
    comparison = Image.new("RGB", (width * 3, height))

    def image_from_rgb(pixels: RgbPixels):
        image = Image.new("RGB", (width, height))
        image.putdata([pixel for row in pixels for pixel in row])
        return image

    def image_from_gray(pixels: GrayPixels):
        image = Image.new("L", (width, height))
        image.putdata([pixel for row in pixels for pixel in row])
        return image.convert("RGB")

    comparison.paste(image_from_rgb(reference), (0, 0))
    comparison.paste(image_from_rgb(rgb332), (width, 0))
    comparison.paste(image_from_gray(grayscale), (width * 2, 0))
    comparison.save(path)


def _run_resolution(
    rgb_source: RgbPixels,
    gray_source: GrayPixels,
    *,
    width: int,
    height: int,
    levels: int,
    payload_limit: int,
    output_directory: Path,
) -> dict[str, object]:
    rgb_reference = _resize(rgb_source, width, height)
    gray_reference = _resize(gray_source, width, height)

    rgb_encoded = Rgb332Encoder(width=width, height=height).encode(rgb_source)
    rgb_reconstructed = Rgb332Decoder().decode(rgb_encoded)
    gray_encoded = ImageEncoder(
        width=width,
        height=height,
        levels=levels,
    ).encode(gray_source)
    gray_reconstructed = ImageDecoder().decode(gray_encoded)

    output_directory.mkdir(parents=True, exist_ok=True)
    resolution_name = f"{width}x{height}"
    paths = {
        "rgb_reference": output_directory / f"{resolution_name}-rgb-reference.png",
        "rgb332_reconstructed": output_directory / f"{resolution_name}-rgb332.png",
        "grayscale_reference": output_directory / f"{resolution_name}-gray-reference.png",
        "grayscale_reconstructed": output_directory / f"{resolution_name}-gray{levels}.png",
        "comparison": output_directory / f"{resolution_name}-comparison.png",
    }
    _save_rgb(rgb_reference, paths["rgb_reference"])
    _save_rgb(rgb_reconstructed, paths["rgb332_reconstructed"])
    _save_gray(gray_reference, paths["grayscale_reference"])
    _save_gray(gray_reconstructed, paths["grayscale_reconstructed"])
    _save_comparison(
        rgb_reference,
        rgb_reconstructed,
        gray_reconstructed,
        paths["comparison"],
    )

    return {
        "resolution": resolution_name,
        "rgb332": {
            **_mm1_cost(len(rgb_encoded.data), payload_limit),
            "quality": _quality_rgb(rgb_reference, rgb_reconstructed),
        },
        "grayscale": {
            "levels": levels,
            **_mm1_cost(len(gray_encoded.data), payload_limit),
            "quality": _quality_gray(gray_reference, gray_reconstructed),
        },
        "artifacts": {
            name: str(path)
            for name, path in paths.items()
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare the isolated RGB332 codec with grayscale"
    )
    parser.add_argument("--image", required=True, help="input image path")
    parser.add_argument(
        "--output-dir",
        default="artifacts/rgb332",
        help="directory for images and JSON results",
    )
    parser.add_argument(
        "--resolution",
        action="append",
        type=_resolution_argument,
        help="32x32 or 64x64; repeat to select both",
    )
    parser.add_argument(
        "--levels",
        type=int,
        default=16,
        choices=(2, 4, 8, 16, 256),
        help="grayscale levels; 16 is the primary baseline",
    )
    parser.add_argument(
        "--payload",
        type=int,
        default=64,
        help="payload limit used for analytical MM1 cost",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if Image is None:
        parser.error("Pillow is required; install the local extra")
    if not 1 <= args.payload <= 255:
        parser.error("payload must be between 1 and 255")

    input_path = Path(args.image)
    output_directory = Path(args.output_dir)
    resolutions = args.resolution or [(32, 32), (64, 64)]
    rgb_source, gray_source = _load_pixels(input_path)
    results = [
        _run_resolution(
            rgb_source,
            gray_source,
            width=width,
            height=height,
            levels=args.levels,
            payload_limit=args.payload,
            output_directory=output_directory,
        )
        for width, height in resolutions
    ]

    output_directory.mkdir(parents=True, exist_ok=True)
    result_path = output_directory / "results.json"
    result_path.write_text(
        json.dumps(
            {
                "input": str(input_path),
                "payload_limit": args.payload,
                "grayscale_levels": args.levels,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    for result in results:
        rgb = result["rgb332"]
        gray = result["grayscale"]
        print(
            f"{result['resolution']}: "
            f"RGB332 bytes={rgb['encoded_bytes']} "
            f"fragments={rgb['fragment_count']} "
            f"overhead={rgb['overhead_bytes']} "
            f"PSNR={rgb['quality']['psnr_db']}"
        )
        print(
            f"{result['resolution']}: "
            f"gray{gray['levels']} bytes={gray['encoded_bytes']} "
            f"fragments={gray['fragment_count']} "
            f"overhead={gray['overhead_bytes']} "
            f"PSNR={gray['quality']['psnr_db']}"
        )
    print(f"results={result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
