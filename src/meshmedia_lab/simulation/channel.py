"""A small channel simulator for loss and corruption experiments."""

from collections.abc import Iterable
from dataclasses import dataclass
import random


@dataclass(frozen=True, slots=True)
class ChannelConfig:
    """Conditions applied to each transmitted packet."""

    max_payload_size: int | None = None
    loss_rate: float = 0.0
    corruption_rate: float = 0.0
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.max_payload_size is not None and self.max_payload_size <= 0:
            raise ValueError("max_payload_size must be positive")
        if not 0.0 <= self.loss_rate <= 1.0:
            raise ValueError("loss_rate must be between 0 and 1")
        if not 0.0 <= self.corruption_rate <= 1.0:
            raise ValueError("corruption_rate must be between 0 and 1")


class ChannelSimulator:
    """Apply repeatable loss and bit corruption to packet bytes."""

    def __init__(self, config: ChannelConfig | None = None) -> None:
        self.config = config or ChannelConfig()
        self._random = random.Random(self.config.seed)

    def transmit(self, payloads: Iterable[bytes]) -> tuple[bytes, ...]:
        delivered: list[bytes] = []
        for payload in payloads:
            packet = bytes(payload)
            if (
                self.config.max_payload_size is not None
                and len(packet) > self.config.max_payload_size
            ):
                raise ValueError("packet exceeds the channel payload limit")
            if self._random.random() < self.config.loss_rate:
                continue
            if packet and self._random.random() < self.config.corruption_rate:
                packet = self._corrupt(packet)
            delivered.append(packet)
        return tuple(delivered)

    def _corrupt(self, payload: bytes) -> bytes:
        corrupted = bytearray(payload)
        byte_index = self._random.randrange(len(corrupted))
        bit = 1 << self._random.randrange(8)
        corrupted[byte_index] ^= bit
        return bytes(corrupted)
