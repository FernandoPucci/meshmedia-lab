"""Local image transmitter CLI."""

from __future__ import annotations

import argparse
import logging

from meshmedia_lab.codec.encoder import ImageEncoder
from meshmedia_lab.codec.rgb332 import Rgb332Encoder
from meshmedia_lab.fec import (
    FecConfig,
    FecConfigurationError,
    IncompleteBlockPolicy,
    PaddingPolicy,
    ReedSolomonEncoder,
    prepare_fec_transmission,
)
from meshmedia_lab.protocol.descriptor import TransmissionDescriptor
from meshmedia_lab.protocol.fec import FecPacketizer
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.transport.udp import UdpSender

from .common import (
    PacketStats,
    configure_logging,
    log_packet,
    log_summary,
    parse_resolution,
)
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
        "--fec-algorithm",
        choices=("none", "reed_solomon"),
        default="none",
        help="optional FEC algorithm; none is the default",
    )
    parser.add_argument(
        "--fec-data-symbols",
        type=int,
        help="number of source symbols per FEC block",
    )
    parser.add_argument(
        "--fec-repair-symbols",
        type=int,
        help="number of repair symbols per FEC block",
    )
    parser.add_argument(
        "--fec-symbol-size",
        type=int,
        default=1,
        help="FEC symbol size in bytes",
    )
    parser.add_argument(
        "--fec-interleaving-depth",
        type=int,
        default=0,
        help="FEC interleaving depth; Reed-Solomon currently requires zero",
    )
    parser.add_argument(
        "--fec-padding-policy",
        choices=("reject", "zero_pad"),
        default="zero_pad",
        help="policy for padding the final FEC block",
    )
    parser.add_argument(
        "--fec-incomplete-block-policy",
        choices=("reject", "pad_to_k"),
        default="pad_to_k",
        help="policy for a final block with fewer than k symbols",
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

    fec_config = None
    fec_encoder = None
    if args.fec_algorithm != "none":
        if args.fec_data_symbols is None or args.fec_repair_symbols is None:
            raise SystemExit(
                "--fec-data-symbols and --fec-repair-symbols are required "
                "when FEC is enabled"
            )
        try:
            fec_config = FecConfig(
                algorithm_id=args.fec_algorithm,
                symbol_size=args.fec_symbol_size,
                data_symbols=args.fec_data_symbols,
                repair_symbols=args.fec_repair_symbols,
                block_symbols=args.fec_data_symbols + args.fec_repair_symbols,
                interleaving_depth=args.fec_interleaving_depth,
                padding_policy=PaddingPolicy(args.fec_padding_policy),
                incomplete_block_policy=IncompleteBlockPolicy(
                    args.fec_incomplete_block_policy
                ),
            )
            fec_encoder = ReedSolomonEncoder()
        except FecConfigurationError as error:
            raise SystemExit(f"invalid FEC configuration: {error}") from error

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
    fragmenter = Fragmenter(max_payload_size=args.payload)
    fec_transmission = None
    if fec_config is None:
        packets = fragmenter.fragment(
            encoded.data,
            image_id=args.image_id,
            metadata=encoded.metadata,
            descriptor=descriptor,
        )
    else:
        if fec_encoder is None:
            raise SystemExit("FEC encoder was not initialized")
        fec_transmission = prepare_fec_transmission(
            encoded.data,
            fec_config,
            fec_encoder,
        )
        packets = FecPacketizer(
            max_payload_size=args.payload,
        ).packetize(
            fec_transmission,
            image_id=args.image_id,
            metadata=encoded.metadata,
            descriptor=descriptor,
        )
    LOGGER.info(
        "prepared image_id=%d codec=%s encoded_bytes=%d messages=%d "
        "payload_limit=%d mode=%s fec_algorithm=%s",
        args.image_id,
        args.codec,
        len(encoded.data),
        len(packets),
        args.payload,
        args.transmission_mode,
        args.fec_algorithm,
    )
    if fec_transmission is not None:
        LOGGER.info(
            "prepared FEC blocks=%d source_symbols=%d repair_symbols=%d",
            fec_transmission.total_blocks,
            fec_transmission.total_blocks * fec_config.data_symbols,
            fec_transmission.repair_symbol_count,
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
