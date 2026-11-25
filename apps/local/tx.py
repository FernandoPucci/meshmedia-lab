"""Local image transmitter CLI."""

from __future__ import annotations

import argparse
import logging

from meshmedia_lab.codec.encoder import ImageEncoder
from meshmedia_lab.codec.rgb332 import Rgb332Encoder
from meshmedia_lab.protocol.descriptor import TransmissionDescriptor
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.transport.udp import UdpSender

from .common import PacketStats, configure_logging, log_packet, log_summary, parse_resolution
from .image_io import load_grayscale_pixels, load_rgb_pixels

LOGGER = logging.getLogger("meshmedia.local.tx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transmit an image over local UDP")
    parser.add_argument("--image", required=True, help="input image path")
    parser.add_argument("--host", default="127.0.0.1", help="RX host")
    parser.add_argument("--port", type=int, default=9000, help="RX UDP port")
    parser.add_argument("--resolution", default="32x32", help="target resolution")
    parser.add_argument(
        "--codec",
        choices=("grayscale", "rgb332"),
        default="grayscale",
        help="image codec; grayscale is the default",
    )
    parser.add_argument(
        "--levels",
        type=int,
        default=16,
        choices=(2, 4, 8, 16, 256),
        help="grayscale levels; ignored when codec is rgb332",
    )
    parser.add_argument(
        "--payload",
        type=int,
        default=64,
        help="maximum encoded payload bytes per packet",
    )
    parser.add_argument("--image-id", type=int, default=1, help="transmission image ID")
    parser.add_argument(
        "--transmission-mode",
        choices=("legacy", "descriptor"),
        default="legacy",
        help="legacy default; descriptor requires an updated receiver",
    )
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

    if args.codec == "grayscale":
        pixels = load_grayscale_pixels(args.image)
        encoded = ImageEncoder(width=width, height=height, levels=args.levels).encode(
            pixels
        )
    else:
        pixels = load_rgb_pixels(args.image)
        encoded = Rgb332Encoder(width=width, height=height).encode(pixels)
    LOGGER.info(
        "loaded image path=%s codec=%s source_resolution=%dx%d "
        "target_resolution=%dx%d",
        args.image,
        args.codec,
        len(pixels[0]),
        len(pixels),
        width,
        height,
    )

    descriptor = (
        TransmissionDescriptor(metadata=encoded.metadata, encoded_length=len(encoded.data))
        if args.transmission_mode == "descriptor"
        else None
    )
    packets = Fragmenter(max_payload_size=args.payload).fragment(
        encoded.data,
        image_id=args.image_id,
        metadata=encoded.metadata,
        descriptor=descriptor,
    )
    LOGGER.info(
        "prepared image_id=%d codec=%s encoded_bytes=%d messages=%d "
        "payload_limit=%d mode=%s",
        args.image_id,
        args.codec,
        len(encoded.data),
        len(packets),
        args.payload,
        args.transmission_mode,
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
