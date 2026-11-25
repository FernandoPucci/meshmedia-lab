"""Local end-to-end image transmission pipeline."""

from collections.abc import Sequence
from dataclasses import dataclass

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import EncodedImage, ImageEncoder
from meshmedia_lab.codec.rgb332 import EncodedRgb332Image, Rgb332Decoder, Rgb332Encoder
from meshmedia_lab.fec import (
    FecConfig,
    FecDecoder,
    FecEncoder,
    FecTransmission,
    prepare_fec_transmission,
)
from meshmedia_lab.media import CODEC_GRAYSCALE_PACKED, CODEC_RGB332
from meshmedia_lab.protocol.descriptor import TransmissionDescriptor
from meshmedia_lab.protocol.fec import (
    FecPacketizer,
    FecReassembler,
    FecReassemblyError,
)
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
    fec_transmission: FecTransmission | None = None


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
        transmission_mode: str = "legacy",
        fec_encoder: FecEncoder | None = None,
        fec_decoder: FecDecoder | None = None,
        fec_config: FecConfig | None = None,
    ) -> None:
        if codec not in ("grayscale", "rgb332"):
            raise ValueError("codec must be 'grayscale' or 'rgb332'")
        if transmission_mode not in ("legacy", "descriptor"):
            raise ValueError("transmission_mode must be 'legacy' or 'descriptor'")
        fec_values = (fec_encoder, fec_decoder, fec_config)
        if any(value is not None for value in fec_values) and not all(
            value is not None for value in fec_values
        ):
            raise ValueError(
                "fec_encoder, fec_decoder and fec_config must be provided together"
            )
        self.transmission_mode = transmission_mode
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
        self.fec_encoder = fec_encoder
        self.fec_decoder = fec_decoder
        self.fec_config = fec_config

    def transmit(
        self,
        pixels: Sequence[Sequence[int]] | Sequence[Sequence[tuple[int, int, int]]],
        *,
        image_id: int = 1,
        channel: ChannelSimulator | None = None,
    ) -> TransmissionResult:
        encoded = self.encoder.encode(pixels)
        descriptor = (
            TransmissionDescriptor(
                metadata=encoded.metadata,
                encoded_length=len(encoded.data),
            )
            if self.transmission_mode == "descriptor"
            else None
        )
        fec_transmission = None
        if self.fec_config is None:
            packets = self.fragmenter.fragment(
                encoded.data,
                image_id=image_id,
                metadata=encoded.metadata,
                descriptor=descriptor,
            )
        else:
            if self.fec_encoder is None or self.fec_decoder is None:
                raise TransmissionError("FEC pipeline is missing an encoder or decoder")
            fec_transmission = prepare_fec_transmission(
                encoded.data,
                self.fec_config,
                self.fec_encoder,
            )
            packets = FecPacketizer(
                max_payload_size=self.fragmenter.max_payload_size,
            ).packetize(
                fec_transmission,
                image_id=image_id,
                metadata=encoded.metadata,
                descriptor=descriptor,
            )
        raw_packets = tuple(packet.to_bytes() for packet in packets)
        delivered = channel.transmit(raw_packets) if channel else raw_packets

        receiver = Receiver()
        reassembler = Reassembler() if fec_transmission is None else None
        fec_reassembler = (
            None if fec_transmission is None else FecReassembler()
        )
        received_count = 0

        for raw_packet in delivered:
            try:
                packet = receiver.receive(raw_packet)
                if fec_reassembler is not None:
                    fec_reassembler.add(packet)
                else:
                    if reassembler is None:
                        raise TransmissionError("missing legacy reassembler")
                    reassembler.add(packet)
            except (ValueError, ReassemblyError, FecReassemblyError):
                continue
            received_count += 1

        if fec_reassembler is not None:
            if fec_reassembler.rejected:
                raise TransmissionError("FEC transmission was rejected")
            if not fec_reassembler.can_decode:
                missing = ", ".join(
                    f"{block}:{symbol}"
                    for block, symbol in fec_reassembler.missing_symbols
                )
                raise TransmissionError(
                    f"incomplete FEC transmission; missing symbols: {missing}"
                )
            try:
                encoded_data = fec_reassembler.decode(self.fec_decoder)
            except FecReassemblyError as error:
                raise TransmissionError(str(error)) from error
            metadata = fec_reassembler.metadata
        else:
            if reassembler is None:
                raise TransmissionError("missing legacy reassembler")
            if reassembler.rejected:
                raise TransmissionError("extended transmission was rejected")
            if not reassembler.is_complete:
                missing = ", ".join(
                    str(number) for number in reassembler.missing_fragments
                )
                raise TransmissionError(
                    f"incomplete transmission; missing fragments: {missing}"
                )
            encoded_data = reassembler.assemble()
            metadata = reassembler.metadata

        if metadata is None:
            raise TransmissionError("transmission completed without image metadata")

        if metadata.codec == CODEC_GRAYSCALE_PACKED:
            reconstructed = EncodedImage(
                width=metadata.width,
                height=metadata.height,
                levels=metadata.levels,
                data=encoded_data,
            )
        elif metadata.codec == CODEC_RGB332:
            reconstructed = EncodedRgb332Image(
                width=metadata.width,
                height=metadata.height,
                data=encoded_data,
            )
        else:
            raise TransmissionError(
                f"unsupported image codec: {metadata.codec}"
            )
        image = self.decoder.decode(reconstructed)

        return TransmissionResult(
            image=image,
            encoded_size=len(encoded.data),
            packets_sent=len(packets),
            packets_received=received_count,
            fec_transmission=fec_transmission,
        )
