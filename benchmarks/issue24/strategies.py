"""Strategy adapters for the Issue #24 local experiment."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import EncodedImage, ImageEncoder
from meshmedia_lab.fec import (
    DecodeResult,
    FecTransmission,
    ReedSolomonDecoder,
    ReedSolomonEncoder,
    block_metadata_for_index,
    prepare_fec_transmission,
)
from meshmedia_lab.media import ImageMetadata
from meshmedia_lab.protocol.fec import (
    FecPacketizer,
    FecReassembler,
    FecReassemblyError,
    FecSymbolFrame,
)
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.protocol.packet import Packet
from meshmedia_lab.protocol.reassembler import Reassembler, ReassemblyError
from meshmedia_lab.transport.receiver import Receiver

from .config import StrategyName, fec_config, strategy_id
from .faults import DeliveredUnit, WireUnit
from .fixtures import GrayPixels

MM1_HEADER_BYTES = 19
CRC_BYTES_PER_PACKET = 2


@dataclass(frozen=True, slots=True)
class PreparedTransmission:
    """Encoded and packetized data before channel faults are applied."""

    strategy: StrategyName
    strategy_id: str
    fec_variant: tuple[int, int] | None
    encoded: EncodedImage
    fec_transmission: FecTransmission | None
    units: tuple[WireUnit, ...]
    encoded_bytes: int
    padded_source_bytes: int
    padding_bytes: int
    repair_bytes: int
    fec_frame_bytes: int
    payload_bytes: int
    header_bytes: int
    crc_bytes: int
    wire_bytes: int
    message_unit: str

    @property
    def total_blocks(self) -> int:
        return (
            self.fec_transmission.total_blocks
            if self.fec_transmission is not None
            else 0
        )


@dataclass(frozen=True, slots=True)
class BlockDecode:
    """Diagnostic outcome for one FEC block."""

    block_index: int
    success: bool
    recovered_symbols: int
    missing_symbols: int
    invalid_symbols: int
    reason: str | None


@dataclass(frozen=True, slots=True)
class DecodeSummary:
    """FEC decode result with block-level diagnostics."""

    source_data: bytes | None
    blocks_total: int
    blocks_decoded: int
    blocks_recovered: int
    blocks_failed: int
    symbols_recovered: int
    symbols_missing: int
    symbols_invalid: int
    block_results: tuple[BlockDecode, ...]

    @property
    def success(self) -> bool:
        return self.source_data is not None and self.blocks_failed == 0

    @property
    def failure_reasons(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    result.reason
                    for result in self.block_results
                    if result.reason is not None
                }
            )
        )


@dataclass(frozen=True, slots=True)
class StrategyOutcome:
    """Reception and reconstruction measurements for one strategy."""

    reconstructed_encoded: bytes | None
    reconstructed_pixels: GrayPixels | None
    messages_received: int
    messages_validated: int
    messages_crc_rejected: int | None
    messages_used_to_conclude: int | None
    completion_message_index: int | None
    final_decode: DecodeSummary | None
    first_decode: DecodeSummary | None
    failure_reason: str | None


def _image_decoder(metadata: ImageMetadata, data: bytes) -> GrayPixels:
    if metadata.codec != 0x01:
        raise ValueError(f"unexpected codec for grayscale experiment: {metadata.codec}")
    encoded = EncodedImage(
        width=metadata.width,
        height=metadata.height,
        levels=metadata.levels,
        data=data,
    )
    return ImageDecoder().decode(encoded)


def _frame_metadata_bytes(frame: FecSymbolFrame) -> int:
    return len(frame.to_bytes()) - len(frame.symbol.data)


def _build_fec_units(
    frames: Iterable[FecSymbolFrame],
    *,
    strategy: StrategyName,
    packets: Iterable[Packet] | None = None,
) -> tuple[WireUnit, ...]:
    units: list[WireUnit] = []
    packet_values = tuple(packets) if packets is not None else ()
    for ordinal, frame in enumerate(frames):
        frame_bytes = frame.to_bytes()
        if strategy == "crc+rs":
            if ordinal >= len(packet_values):
                raise ValueError("FEC packet list is shorter than its frames")
            raw = packet_values[ordinal].to_bytes()
            content_offset = (
                MM1_HEADER_BYTES + _frame_metadata_bytes(frame)
            )
            message_unit = "mm1"
        else:
            raw = frame_bytes
            content_offset = _frame_metadata_bytes(frame)
            message_unit = "rs_frame"
        units.append(
            WireUnit(
                ordinal=ordinal,
                raw=raw,
                content_offset=content_offset,
                content_length=len(frame.symbol.data),
                message_unit=message_unit,
                block_index=frame.block_index,
                symbol_index=frame.symbol.index,
            )
        )
    return tuple(units)


def prepare_transmission(
    pixels: GrayPixels,
    *,
    width: int,
    height: int,
    strategy: StrategyName,
    fec_variant: tuple[int, int] | None,
    image_id: int = 1,
    payload_limit: int = 64,
    encoded_image: EncodedImage | None = None,
) -> PreparedTransmission:
    """Encode and packetize one image through a selected strategy."""

    if strategy == "crc-only" and fec_variant is not None:
        raise ValueError("CRC-only cannot receive an FEC variant")
    if strategy != "crc-only" and fec_variant is None:
        raise ValueError(f"{strategy} requires an FEC variant")

    encoded = encoded_image or ImageEncoder(
        width=width,
        height=height,
        levels=16,
    ).encode(pixels)
    encoded_bytes = len(encoded.data)
    if strategy == "crc-only":
        packets = Fragmenter(max_payload_size=payload_limit).fragment(
            encoded.data,
            image_id=image_id,
            metadata=encoded.metadata,
        )
        units = tuple(
            WireUnit(
                ordinal=index,
                raw=packet.to_bytes(),
                content_offset=MM1_HEADER_BYTES,
                content_length=len(packet.payload),
                message_unit="mm1",
            )
            for index, packet in enumerate(packets)
        )
        wire_bytes = sum(len(unit.raw) for unit in units)
        return PreparedTransmission(
            strategy=strategy,
            strategy_id=strategy_id(strategy, fec_variant),
            fec_variant=None,
            encoded=encoded,
            fec_transmission=None,
            units=units,
            encoded_bytes=encoded_bytes,
            padded_source_bytes=encoded_bytes,
            padding_bytes=0,
            repair_bytes=0,
            fec_frame_bytes=0,
            payload_bytes=sum(len(packet.payload) for packet in packets),
            header_bytes=len(packets) * MM1_HEADER_BYTES,
            crc_bytes=len(packets) * CRC_BYTES_PER_PACKET,
            wire_bytes=wire_bytes,
            message_unit="mm1",
        )

    if fec_variant is None:
        raise ValueError("FEC variant is required")
    data_symbols, repair_symbols = fec_variant
    config = fec_config(data_symbols, repair_symbols)
    transmission = prepare_fec_transmission(
        encoded.data,
        config,
        ReedSolomonEncoder(),
    )
    frames = tuple(
        FecSymbolFrame(
            config=config,
            encoded_length=transmission.encoded_length,
            total_blocks=transmission.total_blocks,
            block_index=block.block_index,
            metadata=block.metadata,
            symbol=symbol,
        )
        for block in transmission.blocks
        for symbol in block.symbols
    )

    packets: tuple[Packet, ...] | None = None
    if strategy == "crc+rs":
        packets = FecPacketizer(max_payload_size=payload_limit).packetize(
            transmission,
            image_id=image_id,
            metadata=encoded.metadata,
        )
        if len(packets) != len(frames):
            raise ValueError("FEC packet count does not match frame count")

    units = _build_fec_units(
        frames,
        strategy=strategy,
        packets=packets,
    )
    padded_source_bytes = (
        transmission.total_blocks * config.data_symbols * config.symbol_size
    )
    padding_bytes = sum(
        block.metadata.padding_length for block in transmission.blocks
    )
    repair_bytes = (
        transmission.repair_symbol_count * config.symbol_size
    )
    fec_frame_bytes = sum(_frame_metadata_bytes(frame) for frame in frames)
    if strategy == "crc+rs":
        payload_bytes = sum(len(packet.payload) for packet in packets or ())
        header_bytes = len(units) * MM1_HEADER_BYTES
        crc_bytes = len(units) * CRC_BYTES_PER_PACKET
    else:
        payload_bytes = sum(len(unit.raw) for unit in units)
        header_bytes = 0
        crc_bytes = 0

    return PreparedTransmission(
        strategy=strategy,
        strategy_id=strategy_id(strategy, fec_variant),
        fec_variant=fec_variant,
        encoded=encoded,
        fec_transmission=transmission,
        units=units,
        encoded_bytes=encoded_bytes,
        padded_source_bytes=padded_source_bytes,
        padding_bytes=padding_bytes,
        repair_bytes=repair_bytes,
        fec_frame_bytes=fec_frame_bytes,
        payload_bytes=payload_bytes,
        header_bytes=header_bytes,
        crc_bytes=crc_bytes,
        wire_bytes=sum(len(unit.raw) for unit in units),
        message_unit="mm1" if strategy == "crc+rs" else "rs_frame",
    )


def _decode_frames(
    frames: dict[tuple[int, int], FecSymbolFrame],
    transmission: FecTransmission,
    decoder: ReedSolomonDecoder,
) -> DecodeSummary:
    block_results: list[BlockDecode] = []
    source_blocks: list[bytes] = []
    for block in transmission.blocks:
        block_frames = tuple(
            frame
            for (block_index, _), frame in frames.items()
            if block_index == block.block_index
        )
        received = tuple(
            frame.symbol
            for frame in sorted(
                block_frames,
                key=lambda frame: frame.symbol.index,
            )
        )
        received_indices = {symbol.index for symbol in received}
        erasures = tuple(
            index
            for index in range(transmission.config.block_symbols)
            if index not in received_indices
        )
        metadata = block_metadata_for_index(
            transmission.encoded_length,
            transmission.config,
            block.block_index,
            total_blocks=transmission.total_blocks,
        )
        try:
            result: DecodeResult = decoder.decode(
                received,
                erasures,
                transmission.config,
                metadata,
            )
        except ValueError as error:
            block_results.append(
                BlockDecode(
                    block_index=block.block_index,
                    success=False,
                    recovered_symbols=0,
                    missing_symbols=len(erasures),
                    invalid_symbols=0,
                    reason=f"decoder_error:{error}",
                )
            )
            continue

        reason = result.reason.value if result.reason is not None else None
        block_results.append(
            BlockDecode(
                block_index=block.block_index,
                success=result.success,
                recovered_symbols=result.recovered_count,
                missing_symbols=len(result.missing_indices),
                invalid_symbols=len(result.invalid_indices),
                reason=reason,
            )
        )
        if result.success and result.source_block is not None:
            source_blocks.append(result.source_block)

    failed = sum(not result.success for result in block_results)
    decoded = len(block_results) - failed
    recovered = sum(
        result.success and result.recovered_symbols > 0
        for result in block_results
    )
    summary = DecodeSummary(
        source_data=(
            b"".join(source_blocks)
            if failed == 0 and len(source_blocks) == transmission.total_blocks
            else None
        ),
        blocks_total=transmission.total_blocks,
        blocks_decoded=decoded,
        blocks_recovered=recovered,
        blocks_failed=failed,
        symbols_recovered=sum(
            result.recovered_symbols for result in block_results
        ),
        symbols_missing=sum(
            result.missing_symbols for result in block_results
        ),
        symbols_invalid=sum(
            result.invalid_symbols for result in block_results
        ),
        block_results=tuple(block_results),
    )
    return summary


def _outcome(
    *,
    reconstructed_encoded: bytes | None,
    reconstructed_pixels: GrayPixels | None,
    messages_received: int,
    messages_validated: int,
    messages_crc_rejected: int | None,
    messages_used_to_conclude: int | None,
    completion_message_index: int | None,
    final_decode: DecodeSummary | None,
    first_decode: DecodeSummary | None,
    failure_reason: str | None,
) -> StrategyOutcome:
    return StrategyOutcome(
        reconstructed_encoded=reconstructed_encoded,
        reconstructed_pixels=reconstructed_pixels,
        messages_received=messages_received,
        messages_validated=messages_validated,
        messages_crc_rejected=messages_crc_rejected,
        messages_used_to_conclude=messages_used_to_conclude,
        completion_message_index=completion_message_index,
        final_decode=final_decode,
        first_decode=first_decode,
        failure_reason=failure_reason,
    )


def receive_crc_only(
    prepared: PreparedTransmission,
    delivered: tuple[DeliveredUnit, ...],
) -> StrategyOutcome:
    """Receive a CRC-only transmission through the legacy reassembler."""

    receiver = Receiver()
    reassembler = Reassembler()
    messages_validated = 0
    crc_rejected = 0
    completion_message_index: int | None = None
    messages_used_to_conclude: int | None = None
    reconstructed_encoded: bytes | None = None
    reconstructed_pixels: GrayPixels | None = None
    failure_reason: str | None = None

    for delivered_unit in delivered:
        try:
            packet = receiver.receive(delivered_unit.raw)
        except ValueError:
            crc_rejected += 1
            continue
        messages_validated += 1
        try:
            reassembler.add(packet)
        except ReassemblyError as error:
            failure_reason = f"reassembly_error:{error}"
            continue
        if completion_message_index is None and reassembler.is_complete:
            try:
                reconstructed_encoded = reassembler.assemble()
                reconstructed_pixels = _image_decoder(
                    prepared.encoded.metadata,
                    reconstructed_encoded,
                )
                completion_message_index = delivered_unit.unit.ordinal + 1
                messages_used_to_conclude = messages_validated
            except ValueError as error:
                failure_reason = f"image_decode_error:{error}"

    if completion_message_index is None and failure_reason is None:
        failure_reason = "incomplete_transmission"

    return _outcome(
        reconstructed_encoded=reconstructed_encoded,
        reconstructed_pixels=reconstructed_pixels,
        messages_received=len(delivered),
        messages_validated=messages_validated,
        messages_crc_rejected=crc_rejected,
        messages_used_to_conclude=messages_used_to_conclude,
        completion_message_index=completion_message_index,
        final_decode=None,
        first_decode=None,
        failure_reason=failure_reason,
    )


def receive_fec(
    prepared: PreparedTransmission,
    delivered: tuple[DeliveredUnit, ...],
) -> StrategyOutcome:
    """Receive CRC+RS or RS-only units and decode blocks incrementally."""

    if prepared.fec_transmission is None:
        raise ValueError("FEC transmission is required")
    decoder = ReedSolomonDecoder()
    receiver = Receiver() if prepared.strategy == "crc+rs" else None
    reassembler = FecReassembler() if prepared.strategy == "crc+rs" else None
    frames: dict[tuple[int, int], FecSymbolFrame] = {}
    messages_validated = 0
    crc_rejected = 0
    completion_message_index: int | None = None
    messages_used_to_conclude: int | None = None
    first_decode: DecodeSummary | None = None
    final_decode: DecodeSummary | None = None
    failure_reason: str | None = None
    last_attempt_threshold = 0
    block_counts = [0] * prepared.fec_transmission.total_blocks

    for delivered_unit in delivered:
        packet: Packet | None = None
        if receiver is not None:
            try:
                packet = receiver.receive(delivered_unit.raw)
            except ValueError:
                crc_rejected += 1
                continue
            try:
                if reassembler is None:
                    raise FecReassemblyError("missing FEC reassembler")
                reassembler.add(packet)
            except (FecReassemblyError, ValueError) as error:
                failure_reason = f"fec_reassembly_error:{error}"
                continue
            payload = packet.payload
        else:
            payload = delivered_unit.raw

        try:
            frame = FecSymbolFrame.from_bytes(payload)
        except ValueError as error:
            failure_reason = f"fec_frame_error:{error}"
            continue

        messages_validated += 1
        key = (frame.block_index, frame.symbol.index)
        if key in frames:
            failure_reason = "duplicate_fec_symbol"
            continue
        frames[key] = frame
        block_counts[frame.block_index] += 1
        threshold = (
            min(block_counts)
            if len(block_counts) == prepared.fec_transmission.total_blocks
            else 0
        )
        if (
            threshold == prepared.fec_transmission.config.data_symbols
            and last_attempt_threshold == 0
        ):
            candidate = _decode_frames(
                frames,
                prepared.fec_transmission,
                decoder,
            )
            last_attempt_threshold = threshold
            if candidate.success and first_decode is None:
                first_decode = candidate
                completion_message_index = delivered_unit.unit.ordinal + 1
                messages_used_to_conclude = messages_validated

    if (
        prepared.strategy == "crc+rs"
        and reassembler is not None
        and reassembler.rejected
    ):
        failure_reason = failure_reason or "fec_reassembly_rejected"

    final_decode = (
        first_decode
        if first_decode is not None
        else _decode_frames(
            frames,
            prepared.fec_transmission,
            decoder,
        )
    )

    if final_decode.success and final_decode.source_data is not None:
        reconstructed_encoded = final_decode.source_data
        try:
            reconstructed_pixels = _image_decoder(
                prepared.encoded.metadata,
                reconstructed_encoded,
            )
            failure_reason = None
        except ValueError as error:
            reconstructed_pixels = None
            failure_reason = f"image_decode_error:{error}"
    else:
        reconstructed_encoded = None
        reconstructed_pixels = None
        if failure_reason is None:
            reasons = final_decode.failure_reasons
            failure_reason = (
                f"fec_decode_failed:{','.join(reasons)}"
                if reasons
                else "fec_decode_failed"
            )

    return _outcome(
        reconstructed_encoded=reconstructed_encoded,
        reconstructed_pixels=reconstructed_pixels,
        messages_received=len(delivered),
        messages_validated=messages_validated,
        messages_crc_rejected=(
            crc_rejected if prepared.strategy == "crc+rs" else None
        ),
        messages_used_to_conclude=messages_used_to_conclude,
        completion_message_index=completion_message_index,
        final_decode=final_decode,
        first_decode=first_decode,
        failure_reason=failure_reason,
    )


def receive(
    prepared: PreparedTransmission,
    delivered: tuple[DeliveredUnit, ...],
) -> StrategyOutcome:
    """Dispatch reception to the selected strategy."""

    if prepared.strategy == "crc-only":
        return receive_crc_only(prepared, delivered)
    return receive_fec(prepared, delivered)
