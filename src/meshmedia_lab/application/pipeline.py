"""Local end-to-end image transmission pipeline."""

from collections.abc import Sequence
from dataclasses import dataclass

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import EncodedImage, ImageEncoder
from meshmedia_lab.codec.rgb332 import EncodedRgb332Image, Rgb332Decoder, Rgb332Encoder
from meshmedia_lab.media import CODEC_GRAYSCALE_PACKED, CODEC_RGB332
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.protocol.reassembler import Reassembler, ReassemblyError
from meshmedia_lab.simulation.channel import ChannelSimulator
from meshmedia_lab.transport.receiver import Receiver

GrayImage = tuple[tuple[int, ...], ...]
RgbImage = tuple[tuple[tuple[int, int, int], ...], ...]
ImagePixels = GrayImage | RgbImage


class TransmissionError(RuntimeError):
    """Raised when the image cannot be reconstructed."""


@dataclass(frozen=True, slots=True)
class TransmissionResult:
    """Measurements and output from one local transmission."""

    image: ImagePixels
    encoded_size: int
    packets_sent: int
    packets_received: int


class ImagePipeline:
    """Coordinate encoding, packet transport, reassembly and decoding."""

    def __init__(
        self,
        encoder: ImageEncoder | Rgb332Encoder | None = None,
        decoder: ImageDecoder | Rgb332Decoder | None = None,
        fragmenter: Fragmenter | None = None,
        *,
        codec: str = "grayscale",
        width: int = 32,
        height: int = 32,
        levels: int = 16,
    ) -> None:
        if codec not in ("grayscale", "rgb332"):
            raise ValueError("codec must be 'grayscale' or 'rgb332'")
        if encoder is None:
            encoder = (
                ImageEncoder(width=width, height=height, levels=levels)
                if codec == "grayscale"
                else Rgb332Encoder(width=width, height=height)
            )
        if decoder is None:
            decoder = ImageDecoder() if codec == "grayscale" else Rgb332Decoder()
        self.encoder = encoder
        self.decoder = decoder
        self.fragmenter = fragmenter or Fragmenter()

    def transmit(
        self,
        pixels: Sequence[Sequence[int]] | Sequence[Sequence[tuple[int, int, int]]],
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

        if reassembler.metadata.codec == CODEC_GRAYSCALE_PACKED:
            reconstructed = EncodedImage(
                width=reassembler.metadata.width,
                height=reassembler.metadata.height,
                levels=reassembler.metadata.levels,
                data=reassembler.assemble(),
            )
        elif reassembler.metadata.codec == CODEC_RGB332:
            reconstructed = EncodedRgb332Image(
                width=reassembler.metadata.width,
                height=reassembler.metadata.height,
                data=reassembler.assemble(),
            )
        else:
            raise TransmissionError(
                f"unsupported image codec: {reassembler.metadata.codec}"
            )
        image = self.decoder.decode(reconstructed)

        return TransmissionResult(
            image=image,
            encoded_size=len(encoded.data),
            packets_sent=len(packets),
            packets_received=received_count,
        )
