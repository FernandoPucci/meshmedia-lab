"""Local image transmitter CLI."""

from __future__ import annotations

import argparse
import logging

from meshmedia_lab.codec.encoder import ImageEncoder
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.transport.udp import UdpSender

from .common import PacketStats, configure_logging, log_packet, log_summary, parse_resolution
from .image_io import load_grayscale_pixels

LOGGER = logging.getLogger("meshmedia.local.tx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transmit an image over local UDP")
    parser.add_argument("--image", required=True, help="input image path")
    parser.add_argument("--host", default="127.0.0.1", help="RX host")
    parser.add_argument("--port", type=int, default=9000, help="RX UDP port")
    parser.add_argument("--resolution", default="32x32", help="target resolution")
    parser.add_argument(
        "--levels",
        type=int,
        default=16,
        choices=(2, 4, 8, 16, 256),
        help="grayscale levels",
    )
    parser.add_argument(
        "--payload",
        type=int,
        default=64,
        help="maximum encoded payload bytes per packet",
    )
    parser.add_argument("--image-id", type=int, default=1, help="transmission image ID")
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

    pixels = load_grayscale_pixels(args.image)
    LOGGER.info(
        "loaded image path=%s source_resolution=%dx%d target_resolution=%dx%d",
        args.image,
        len(pixels[0]),
        len(pixels),
        width,
        height,
    )

    encoded = ImageEncoder(width=width, height=height, levels=args.levels).encode(pixels)
    packets = Fragmenter(max_payload_size=args.payload).fragment(
        encoded.data,
        image_id=args.image_id,
        metadata=encoded.metadata,
    )
    LOGGER.info(
        "prepared image_id=%d encoded_bytes=%d messages=%d payload_limit=%d",
        args.image_id,
        len(encoded.data),
        len(packets),
        args.payload,
    )

    stats = PacketStats()
    with UdpSender(args.host, args.port) as sender:
        for packet in packets:
            raw = packet.to_bytes()
            sender.send(raw)
            stats.record(packet, raw)
            log_packet(LOGGER, "TX", packet, raw, address=(args.host, args.port))

    log_summary(LOGGER, "TX", stats, expected_packets=len(packets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
