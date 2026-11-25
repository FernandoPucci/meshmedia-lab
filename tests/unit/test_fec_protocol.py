import unittest

from meshmedia_lab.fec import (
    FecConfig,
    IncompleteBlockPolicy,
    PaddingPolicy,
    ReedSolomonDecoder,
    ReedSolomonEncoder,
    prepare_fec_transmission,
)
from meshmedia_lab.media import ImageMetadata
from meshmedia_lab.protocol.descriptor import TransmissionDescriptor
from meshmedia_lab.protocol.fec import (
    FecPacketizer,
    FecReassembler,
    FecReassemblyError,
    FecSymbolFrame,
)
from meshmedia_lab.protocol.packet import Packet


def make_config() -> FecConfig:
    return FecConfig(
        algorithm_id="reed_solomon",
        symbol_size=1,
        data_symbols=4,
        repair_symbols=3,
        block_symbols=7,
        interleaving_depth=0,
        padding_policy=PaddingPolicy.ZERO_PAD,
        incomplete_block_policy=IncompleteBlockPolicy.PAD_TO_K,
    )


class FecProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = make_config()
        self.source = b"abcdefg"
        self.transmission = prepare_fec_transmission(
            self.source,
            self.config,
            ReedSolomonEncoder(),
        )
        self.metadata = ImageMetadata(width=2, height=7, levels=16)

    def test_symbol_frame_round_trip_preserves_configuration_and_metadata(self) -> None:
        block = self.transmission.blocks[1]
        frame = FecSymbolFrame(
            config=self.config,
            encoded_length=self.transmission.encoded_length,
            total_blocks=self.transmission.total_blocks,
            block_index=block.block_index,
            metadata=block.metadata,
            symbol=block.source_symbols[0],
        )

        decoded = FecSymbolFrame.from_bytes(frame.to_bytes())

        self.assertEqual(decoded, frame)
        self.assertEqual(decoded.symbol.index, 0)
        self.assertEqual(decoded.metadata.original_length, 3)
        self.assertEqual(decoded.metadata.padding_length, 1)

    def test_packetizer_and_reassembler_preserve_block_and_symbol_identity(self) -> None:
        packets = FecPacketizer(max_payload_size=64).packetize(
            self.transmission,
            image_id=7,
            metadata=self.metadata,
        )
        reassembler = FecReassembler()
        for packet in reversed(packets):
            reassembler.add(Packet.from_bytes(packet.to_bytes()))

        self.assertTrue(reassembler.is_complete)
        self.assertTrue(reassembler.can_decode)
        self.assertEqual(reassembler.expected_packets, 14)
        self.assertEqual(
            reassembler.decode(ReedSolomonDecoder()),
            self.source,
        )

    def test_reassembler_recovers_missing_symbols_as_erasures(self) -> None:
        packets = FecPacketizer(max_payload_size=64).packetize(
            self.transmission,
            image_id=7,
            metadata=self.metadata,
        )
        omitted = {6, 13}
        reassembler = FecReassembler()
        for packet in packets:
            if packet.fragment_number not in omitted:
                reassembler.add(Packet.from_bytes(packet.to_bytes()))

        self.assertFalse(reassembler.is_complete)
        self.assertTrue(reassembler.can_decode)
        self.assertEqual(reassembler.missing_symbols, ((0, 6), (1, 6)))
        self.assertEqual(
            reassembler.decode(ReedSolomonDecoder()),
            self.source,
        )

    def test_crc_rejected_packet_becomes_an_implicit_erasure(self) -> None:
        packets = FecPacketizer(max_payload_size=64).packetize(
            self.transmission,
            image_id=7,
            metadata=self.metadata,
        )
        corrupted = bytearray(packets[6].to_bytes())
        corrupted[-1] ^= 0x01
        reassembler = FecReassembler()
        for index, packet in enumerate(packets):
            if index == 6:
                with self.assertRaises(ValueError):
                    Packet.from_bytes(corrupted)
                continue
            reassembler.add(Packet.from_bytes(packet.to_bytes()))

        self.assertTrue(reassembler.can_decode)
        self.assertEqual(
            reassembler.decode(ReedSolomonDecoder()),
            self.source,
        )

    def test_reassembler_reports_failure_when_a_block_lacks_k_symbols(self) -> None:
        packets = FecPacketizer(max_payload_size=64).packetize(
            self.transmission,
            image_id=7,
            metadata=self.metadata,
        )
        reassembler = FecReassembler()
        for packet in packets:
            if packet.fragment_number not in {0, 1, 2, 3}:
                reassembler.add(Packet.from_bytes(packet.to_bytes()))

        self.assertFalse(reassembler.can_decode)
        with self.assertRaises(FecReassemblyError):
            reassembler.decode(ReedSolomonDecoder())

    def test_fec_can_coexist_with_the_existing_descriptor_prefix(self) -> None:
        descriptor = TransmissionDescriptor(
            metadata=self.metadata,
            encoded_length=len(self.source),
        )
        packets = FecPacketizer(max_payload_size=144).packetize(
            self.transmission,
            image_id=7,
            metadata=self.metadata,
            descriptor=descriptor,
        )
        reassembler = FecReassembler()
        for packet in packets:
            reassembler.add(Packet.from_bytes(packet.to_bytes()))

        self.assertEqual(reassembler.descriptor, descriptor)
        self.assertEqual(
            reassembler.decode(ReedSolomonDecoder()),
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
