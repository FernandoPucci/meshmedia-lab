"""Local image receiver CLI."""

from __future__ import annotations

import argparse
import logging
import socket

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import EncodedImage
from meshmedia_lab.media import CODEC_GRAYSCALE_PACKED, MEDIA_TYPE_IMAGE
from meshmedia_lab.protocol.packet import Packet, PacketError
from meshmedia_lab.protocol.reassembler import Reassembler, ReassemblyError
from meshmedia_lab.transport.udp import UdpReceiver

from .common import PacketStats, configure_logging, log_packet, log_summary
from .image_io import save_pixels, show_pixels

LOGGER = logging.getLogger("meshmedia.local.rx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Receive an image over local UDP")
    parser.add_argument("--bind", default="127.0.0.1", help="local bind address")
    parser.add_argument("--port", type=int, default=9000, help="local UDP port")
    parser.add_argument(
        "--output",
        default="received.png",
        help="reconstructed image output path",
    )
    parser.add_argument("--display", action="store_true", help="open the image viewer")
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="seconds without a packet before exiting",
    )
    parser.add_argument(
        "--keep-listening",
        action="store_true",
        help="wait for another image after completing one",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    parser.add_argument("--log-file", help="optional log file path")
    return parser


def _decode_packet_stream(reassembler: Reassembler) -> tuple[tuple[int, ...], ...]:
    metadata = reassembler.metadata
    if metadata is None:
        raise ReassemblyError("complete transmission has no metadata")
    if metadata.media_type != MEDIA_TYPE_IMAGE:
        raise ReassemblyError(f"unsupported media type: {metadata.media_type}")
    if metadata.codec != CODEC_GRAYSCALE_PACKED:
        raise ReassemblyError(f"unsupported image codec: {metadata.codec}")

    encoded = EncodedImage(
        width=metadata.width,
        height=metadata.height,
        levels=metadata.levels,
        data=reassembler.assemble(),
    )
    return ImageDecoder().decode(encoded)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level, args.log_file)
    stats = PacketStats()
    reassembler = Reassembler()

    with UdpReceiver(args.bind, args.port, timeout=args.timeout) as receiver:
        LOGGER.info("RX listening address=%s:%d", *receiver.address)
        while True:
            try:
                raw, address = receiver.receive()
            except socket.timeout:
                LOGGER.error("RX timeout waiting for a complete image")
                return 1

            try:
                packet = Packet.from_bytes(raw)
            except PacketError as error:
                stats.invalid_packets += 1
                LOGGER.warning(
                    "RX invalid packet address=%s:%d bytes=%d error=%s raw=%s",
                    address[0],
                    address[1],
                    len(raw),
                    error,
                    raw.hex(" "),
                )
                continue

            try:
                reassembler.add(packet)
            except ReassemblyError as error:
                stats.invalid_packets += 1
                LOGGER.warning("RX rejected packet error=%s", error)
                continue

            stats.record(packet, raw)
            log_packet(LOGGER, "RX", packet, raw, address=address)

            if not reassembler.is_complete:
                continue

            image = _decode_packet_stream(reassembler)
            save_pixels(image, args.output)
            LOGGER.info(
                "image complete image_id=%d messages=%d output=%s",
                packet.image_id,
                packet.total_fragments,
                args.output,
            )
            log_summary(
                LOGGER,
                "RX",
                stats,
                expected_packets=packet.total_fragments,
            )
            if args.display:
                show_pixels(image, f"MeshMedia RX image {packet.image_id}")
            if not args.keep_listening:
                return 0
            stats = PacketStats()
            reassembler = Reassembler()


if __name__ == "__main__":
    raise SystemExit(main())
