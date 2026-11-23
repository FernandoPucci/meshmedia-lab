"""Local end-to-end image transmission pipeline."""

from dataclasses import dataclass

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import EncodedImage, ImageEncoder
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.protocol.reassembler import Reassembler, ReassemblyError
from meshmedia_lab.simulation.channel import ChannelSimulator
from meshmedia_lab.transport.receiver import Receiver


class TransmissionError(RuntimeError):
    """Raised when the image cannot be reconstructed."""


@dataclass(frozen=True, slots=True)
class TransmissionResult:
    """Measurements and output from one local transmission."""

    image: tuple[tuple[int, ...], ...]
    encoded_size: int
    packets_sent: int
    packets_received: int


class ImagePipeline:
    """Coordinate encoding, packet transport, reassembly and decoding."""

    def __init__(
        self,
        encoder: ImageEncoder | None = None,
        decoder: ImageDecoder | None = None,
        fragmenter: Fragmenter | None = None,
    ) -> None:
        self.encoder = encoder or ImageEncoder()
        self.decoder = decoder or ImageDecoder()
        self.fragmenter = fragmenter or Fragmenter()

    def transmit(
        self,
        pixels: tuple[tuple[int, ...], ...] | list[list[int]],
        *,
        image_id: int = 1,
        channel: ChannelSimulator | None = None,
    ) -> TransmissionResult:
        encoded = self.encoder.encode(pixels)
        packets = self.fragmenter.fragment(
            encoded.data,
            image_id=image_id,
            metadata=encoded.metadata,
        )
        raw_packets = tuple(packet.to_bytes() for packet in packets)
        delivered = channel.transmit(raw_packets) if channel else raw_packets

        receiver = Receiver()
        reassembler = Reassembler()
        received_count = 0

        for raw_packet in delivered:
            try:
                packet = receiver.receive(raw_packet)
                reassembler.add(packet)
            except (ValueError, ReassemblyError):
                continue
            received_count += 1

        if not reassembler.is_complete:
            missing = ", ".join(str(number) for number in reassembler.missing_fragments)
            raise TransmissionError(f"incomplete transmission; missing fragments: {missing}")

        if reassembler.metadata is None:
            raise TransmissionError("transmission completed without image metadata")

        reconstructed = EncodedImage(
            width=reassembler.metadata.width,
            height=reassembler.metadata.height,
            levels=reassembler.metadata.levels,
            data=reassembler.assemble(),
        )
        image = self.decoder.decode(reconstructed)

        return TransmissionResult(
            image=image,
            encoded_size=len(encoded.data),
            packets_sent=len(packets),
            packets_received=received_count,
        )
