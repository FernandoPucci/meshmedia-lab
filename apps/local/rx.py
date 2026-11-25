"""Local image receiver CLI."""

from __future__ import annotations

import argparse
import logging

from meshmedia_lab.application.pipeline import ImagePixels
from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import EncodedImage
from meshmedia_lab.codec.rgb332 import EncodedRgb332Image, Rgb332Decoder
from meshmedia_lab.fec import ReedSolomonDecoder
from meshmedia_lab.media import (
    CODEC_GRAYSCALE_PACKED,
    CODEC_RGB332,
    MEDIA_TYPE_IMAGE,
    ImageMetadata,
)
from meshmedia_lab.protocol.fec import (
    FecReassembler,
    FecReassemblyError,
)
from meshmedia_lab.protocol.packet import FLAG_FEC, Packet, PacketError
from meshmedia_lab.protocol.reassembler import Reassembler, ReassemblyError
from meshmedia_lab.transport.udp import UdpReceiver

from .common import PacketStats, configure_logging, log_packet, log_summary
from .image_io import save_pixels, save_rgb_pixels, show_pixels, show_rgb_pixels

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


def _decode_packet_stream(reassembler: Reassembler) -> ImagePixels:
    metadata = reassembler.metadata
    if metadata is None:
        raise ReassemblyError("complete transmission has no metadata")
    return _decode_encoded_data(metadata, reassembler.assemble())


def _decode_encoded_data(metadata: ImageMetadata, data: bytes) -> ImagePixels:
    if metadata.media_type != MEDIA_TYPE_IMAGE:
        raise ReassemblyError(f"unsupported media type: {metadata.media_type}")
    if metadata.codec == CODEC_GRAYSCALE_PACKED:
        encoded = EncodedImage(
            width=metadata.width,
            height=metadata.height,
            levels=metadata.levels,
            data=data,
        )
        return ImageDecoder().decode(encoded)
    if metadata.codec == CODEC_RGB332:
        encoded = EncodedRgb332Image(
            width=metadata.width,
            height=metadata.height,
            data=data,
        )
        return Rgb332Decoder().decode(encoded)
    else:
        raise ReassemblyError(f"unsupported image codec: {metadata.codec}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level, args.log_file)
    stats = PacketStats()
    legacy_reassembler: Reassembler | None = Reassembler()
    fec_reassembler: FecReassembler | None = None
    fec_mode: bool | None = None
    fec_decoder = ReedSolomonDecoder()

    with UdpReceiver(args.bind, args.port, timeout=args.timeout) as receiver:
        LOGGER.info("RX listening address=%s:%d", *receiver.address)
        while True:
            try:
                raw, address = receiver.receive()
            except TimeoutError:
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

            packet_is_fec = bool(packet.flags & FLAG_FEC)
            if fec_mode is None:
                fec_mode = packet_is_fec
                if fec_mode:
                    legacy_reassembler = None
                    fec_reassembler = FecReassembler()
            elif packet_is_fec != fec_mode:
                stats.invalid_packets += 1
                LOGGER.warning("RX rejected packet error=mixed FEC modes")
                continue

            try:
                if fec_mode:
                    if fec_reassembler is None:
                        raise FecReassemblyError("missing FEC reassembler")
                    fec_reassembler.add(packet)
                else:
                    if legacy_reassembler is None:
                        raise ReassemblyError("missing legacy reassembler")
                    legacy_reassembler.add(packet)
            except (ReassemblyError, FecReassemblyError) as error:
                stats.invalid_packets += 1
                LOGGER.warning("RX rejected packet error=%s", error)
                rejected = (
                    fec_reassembler.rejected
                    if fec_mode and fec_reassembler is not None
                    else (
                        legacy_reassembler.rejected
                        if legacy_reassembler is not None
                        else False
                    )
                )
                if rejected:
                    log_summary(LOGGER, "RX", stats)
                    return 1
                continue

            stats.record(packet, raw)
            log_packet(LOGGER, "RX", packet, raw, address=address)

            try:
                if fec_mode:
                    if fec_reassembler is None or not fec_reassembler.can_decode:
                        continue
                    encoded_data = fec_reassembler.decode(fec_decoder)
                    metadata = fec_reassembler.metadata
                    if metadata is None:
                        raise FecReassemblyError(
                            "complete FEC transmission has no metadata"
                        )
                    image = _decode_encoded_data(metadata, encoded_data)
                    reassembler_descriptor = fec_reassembler.descriptor
                    expected_packets = fec_reassembler.expected_packets
                else:
                    if legacy_reassembler is None or not legacy_reassembler.is_complete:
                        continue
                    image = _decode_packet_stream(legacy_reassembler)
                    metadata = legacy_reassembler.metadata
                    reassembler_descriptor = legacy_reassembler.descriptor
                    expected_packets = packet.total_fragments
            except FecReassemblyError as error:
                LOGGER.error("RX cannot recover FEC image: %s", error)
                return 1
            except ValueError as error:
                LOGGER.error("RX cannot decode image: %s", error)
                return 1
            if reassembler_descriptor is not None:
                LOGGER.info(
                    "RX mode=descriptor descriptor_version=%d encoded_length=%d",
                    reassembler_descriptor.version,
                    reassembler_descriptor.encoded_length,
                )
            if fec_mode:
                LOGGER.info(
                    "RX mode=fec algorithm=%s blocks=%d symbols=%d",
                    fec_reassembler.config.algorithm_id
                    if fec_reassembler and fec_reassembler.config
                    else "unknown",
                    fec_reassembler.total_blocks
                    if fec_reassembler and fec_reassembler.total_blocks is not None
                    else 0,
                    fec_reassembler.received_symbols if fec_reassembler else 0,
                )
            if metadata and metadata.codec == CODEC_RGB332:
                save_rgb_pixels(image, args.output)
            else:
                save_pixels(image, args.output)
            LOGGER.info(
                "image complete image_id=%d codec=0x%02x messages=%d output=%s",
                packet.image_id,
                packet.metadata.codec,
                packet.total_fragments,
                args.output,
            )
            log_summary(
                LOGGER,
                "RX",
                stats,
                expected_packets=expected_packets,
            )
            if args.display:
                if packet.metadata.codec == CODEC_RGB332:
                    show_rgb_pixels(image, f"MeshMedia RX image {packet.image_id}")
                else:
                    show_pixels(image, f"MeshMedia RX image {packet.image_id}")
            if not args.keep_listening:
                return 0
            stats = PacketStats()
            legacy_reassembler = Reassembler()
            fec_reassembler = None
            fec_mode = None


if __name__ == "__main__":
    raise SystemExit(main())
