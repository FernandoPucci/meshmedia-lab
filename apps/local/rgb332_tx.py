"""Local UDP transmitter for the isolated RGB332 experiment."""

from __future__ import annotations

import argparse
import logging

from meshmedia_lab.codec.rgb332 import Rgb332Encoder
from meshmedia_lab.transport.udp import UdpSender

from .common import configure_logging, parse_resolution
from .image_io import load_rgb_pixels
from .rgb332_transport import fragment_data

LOGGER = logging.getLogger("meshmedia.local.rgb332.tx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transmit an isolated RGB332 image over local UDP"
    )
    parser.add_argument("--image", required=True, help="input image path")
    parser.add_argument("--host", default="127.0.0.1", help="RX host")
    parser.add_argument("--port", type=int, default=9001, help="RX UDP port")
    parser.add_argument("--resolution", default="32x32", help="target resolution")
    parser.add_argument(
        "--payload",
        type=int,
        default=64,
        help="RGB332 payload bytes per local datagram",
    )
    parser.add_argument("--image-id", type=int, default=38, help="local image ID")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    parser.add_argument("--log-file", help="optional log file path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level, args.log_file)
    width, height = parse_resolution(args.resolution)
    if (width, height) not in ((32, 32), (64, 64)):
        raise SystemExit("RGB332 experiment resolution must be 32x32 or 64x64")
    if not 1 <= args.payload <= 255:
        raise SystemExit("payload must be between 1 and 255")

    pixels = load_rgb_pixels(args.image)
    encoded = Rgb332Encoder(width=width, height=height).encode(pixels)
    datagrams = fragment_data(
        encoded.data,
        image_id=args.image_id,
        width=width,
        height=height,
        payload_size=args.payload,
    )
    LOGGER.info(
        "RGB332 TX prepared image_id=%d source_resolution=%dx%d "
        "target_resolution=%dx%d encoded_bytes=%d messages=%d payload=%d",
        args.image_id,
        len(pixels[0]),
        len(pixels),
        width,
        height,
        len(encoded.data),
        len(datagrams),
        args.payload,
    )

    payload_bytes = 0
    datagram_bytes = 0
    with UdpSender(args.host, args.port) as sender:
        for datagram in datagrams:
            raw = datagram.to_bytes()
            sender.send(raw)
            payload_bytes += len(datagram.payload)
            datagram_bytes += len(raw)
            LOGGER.info(
                "RGB332 TX msg=%d/%d datagram_bytes=%d payload_bytes=%d",
                datagram.fragment_number + 1,
                datagram.total_fragments,
                len(raw),
                len(datagram.payload),
            )

    mm1_overhead = len(datagrams) * 21
    LOGGER.info(
        "RGB332 TX summary messages=%d payload_bytes=%d datagram_bytes=%d "
        "local_overhead_bytes=%d mm1_overhead_bytes=%d mm1_wire_bytes=%d",
        len(datagrams),
        payload_bytes,
        datagram_bytes,
        datagram_bytes - payload_bytes,
        mm1_overhead,
        payload_bytes + mm1_overhead,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
