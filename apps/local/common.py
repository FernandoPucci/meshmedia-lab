"""Shared CLI helpers for the local TX/RX applications."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
import re

from meshmedia_lab.protocol.packet import Packet

_RESOLUTION = re.compile(r"^(\d+)x(\d+)$", re.IGNORECASE)


@dataclass
class PacketStats:
    """Counters shown by the local applications."""

    packets: int = 0
    payload_bytes: int = 0
    wire_bytes: int = 0
    invalid_packets: int = 0

    def record(self, packet: Packet, raw: bytes) -> None:
        self.packets += 1
        self.payload_bytes += len(packet.payload)
        self.wire_bytes += len(raw)

    @property
    def overhead_bytes(self) -> int:
        return self.wire_bytes - self.payload_bytes


def parse_resolution(value: str) -> tuple[int, int]:
    """Parse a resolution in WIDTHxHEIGHT form."""

    match = _RESOLUTION.fullmatch(value.strip())
    if match is None:
        raise ValueError("resolution must use WIDTHxHEIGHT, for example 32x32")
    width, height = (int(part) for part in match.groups())
    if width <= 0 or height <= 0:
        raise ValueError("resolution dimensions must be positive")
    return width, height


def configure_logging(level: str, log_file: str | None = None) -> None:
    """Configure console logging and an optional file sink."""

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
    )


def log_packet(
    logger: logging.Logger,
    direction: str,
    packet: Packet,
    raw: bytes,
    *,
    address: tuple[str, int] | None = None,
) -> None:
    """Log packet metadata and the exact bytes sent over UDP."""

    location = f" address={address[0]}:{address[1]}" if address else ""
    logger.debug(
        "%s packet image_id=%d fragment=%d/%d flags=0x%02x "
        "resolution=%dx%d levels=%d payload_bytes=%d wire_bytes=%d "
        "overhead_bytes=%d%s raw=%s",
        direction,
        packet.image_id,
        packet.fragment_number + 1,
        packet.total_fragments,
        packet.flags,
        packet.metadata.width,
        packet.metadata.height,
        packet.metadata.levels,
        len(packet.payload),
        len(raw),
        len(raw) - len(packet.payload),
        location,
        raw.hex(" "),
    )


def log_summary(
    logger: logging.Logger,
    direction: str,
    stats: PacketStats,
    *,
    expected_packets: int | None = None,
) -> None:
    """Log aggregate transmission counters."""

    expected = f" expected_packets={expected_packets}" if expected_packets else ""
    logger.info(
        "%s summary packets=%d payload_bytes=%d wire_bytes=%d "
        "overhead_bytes=%d invalid_packets=%d%s",
        direction,
        stats.packets,
        stats.payload_bytes,
        stats.wire_bytes,
        stats.overhead_bytes,
        stats.invalid_packets,
        expected,
    )
