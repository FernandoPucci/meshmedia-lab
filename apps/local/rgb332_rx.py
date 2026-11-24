"""Local UDP receiver for the isolated RGB332 experiment."""

from __future__ import annotations

import argparse
import logging
import socket

from meshmedia_lab.codec.rgb332 import EncodedRgb332Image, Rgb332Decoder
from meshmedia_lab.transport.udp import UdpReceiver

from .common import configure_logging
from .image_io import save_rgb_pixels
from .rgb332_transport import Rgb332Datagram, Rgb332DatagramError

LOGGER = logging.getLogger("meshmedia.local.rgb332.rx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Receive an isolated RGB332 image over local UDP"
    )
    parser.add_argument("--bind", default="127.0.0.1", help="local bind address")
    parser.add_argument("--port", type=int, default=9001, help="local UDP port")
    parser.add_argument(
        "--output",
        default="artifacts/rgb332/received-32x32.png",
        help="reconstructed RGB image output path",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="seconds without a datagram before exiting",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    parser.add_argument("--log-file", help="optional log file path")
    return parser


def _add_datagram(
    datagram: Rgb332Datagram,
    *,
    image_id: int | None,
    total_fragments: int | None,
    width: int | None,
    height: int | None,
    fragments: dict[int, bytes],
) -> tuple[int, int, int, int]:
    if image_id is not None and datagram.image_id != image_id:
        raise Rgb332DatagramError("datagram belongs to another image")
    if total_fragments is not None and datagram.total_fragments != total_fragments:
        raise Rgb332DatagramError("datagram has an inconsistent fragment count")
    if width is not None and datagram.width != width:
        raise Rgb332DatagramError("datagram has an inconsistent width")
    if height is not None and datagram.height != height:
        raise Rgb332DatagramError("datagram has an inconsistent height")

    previous = fragments.get(datagram.fragment_number)
    if previous is not None and previous != datagram.payload:
        raise Rgb332DatagramError("duplicate fragment has different payload")
    fragments[datagram.fragment_number] = datagram.payload
    return (
        datagram.image_id,
        datagram.total_fragments,
        datagram.width,
        datagram.height,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level, args.log_file)
    fragments: dict[int, bytes] = {}
    image_id = total_fragments = width = height = None
    message_count = 0
    payload_bytes = 0
    datagram_bytes = 0

    with UdpReceiver(args.bind, args.port, timeout=args.timeout) as receiver:
        LOGGER.info("RGB332 RX listening address=%s:%d", *receiver.address)
        while True:
            try:
                raw, address = receiver.receive()
            except socket.timeout:
                LOGGER.error("RGB332 RX timeout waiting for a complete image")
                return 1

            datagram_bytes += len(raw)
            try:
                datagram = Rgb332Datagram.from_bytes(raw)
                image_id, total_fragments, width, height = _add_datagram(
                    datagram,
                    image_id=image_id,
                    total_fragments=total_fragments,
                    width=width,
                    height=height,
                    fragments=fragments,
                )
            except Rgb332DatagramError as error:
                LOGGER.warning(
                    "RGB332 RX invalid datagram address=%s:%d bytes=%d error=%s",
                    address[0],
                    address[1],
                    len(raw),
                    error,
                )
                continue

            message_count += 1
            payload_bytes += len(datagram.payload)
            LOGGER.info(
                "RGB332 RX msg=%d/%d datagram_bytes=%d payload_bytes=%d",
                datagram.fragment_number + 1,
                datagram.total_fragments,
                len(raw),
                len(datagram.payload),
            )

            if len(fragments) != total_fragments:
                continue

            data = b"".join(fragments[number] for number in range(total_fragments))
            try:
                encoded = EncodedRgb332Image(
                    width=width,
                    height=height,
                    data=data,
                )
                image = Rgb332Decoder().decode(encoded)
            except ValueError as error:
                LOGGER.error("RGB332 RX reconstruction failed: %s", error)
                return 1

            save_rgb_pixels(image, args.output)
            mm1_overhead = total_fragments * 21
            LOGGER.info(
                "RGB332 RX complete image_id=%d resolution=%dx%d output=%s",
                image_id,
                width,
                height,
                args.output,
            )
            LOGGER.info(
                "RGB332 RX summary messages=%d payload_bytes=%d datagram_bytes=%d "
                "local_overhead_bytes=%d mm1_overhead_bytes=%d mm1_wire_bytes=%d",
                message_count,
                payload_bytes,
                datagram_bytes,
                datagram_bytes - payload_bytes,
                mm1_overhead,
                payload_bytes + mm1_overhead,
            )
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
