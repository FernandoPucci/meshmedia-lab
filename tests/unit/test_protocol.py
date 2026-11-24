import unittest

from meshmedia_lab.media import ImageMetadata
from meshmedia_lab.protocol.crc import crc16
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.protocol.packet import (
    FLAG_FIRST_FRAGMENT,
    FLAG_LAST_FRAGMENT,
    Packet,
    PacketError,
)
from meshmedia_lab.protocol.reassembler import Reassembler


class ProtocolTests(unittest.TestCase):
    def test_crc_matches_ccitt_false_reference_vector(self) -> None:
        self.assertEqual(crc16(b"123456789"), 0x29B1)

    def test_packet_round_trip(self) -> None:
        metadata = ImageMetadata(width=32, height=32, levels=16)
        packet = Packet(
            metadata=metadata,
            image_id=7,
            fragment_number=0,
            total_fragments=1,
            payload=b"payload",
            flags=FLAG_FIRST_FRAGMENT | FLAG_LAST_FRAGMENT,
        )

        decoded = Packet.from_bytes(packet.to_bytes())

        self.assertEqual(decoded, packet)
        self.assertEqual(decoded.metadata, metadata)

    def test_metadata_accepts_independent_dimensions_at_128_boundary(self) -> None:
        self.assertEqual(
            ImageMetadata(width=128, height=1, levels=16).width,
            128,
        )
        self.assertEqual(
            ImageMetadata(width=1, height=128, levels=16).height,
            128,
        )

    def test_metadata_rejects_dimensions_above_128(self) -> None:
        with self.assertRaisesRegex(ValueError, "width must be between 1 and 128"):
            ImageMetadata(width=129, height=1, levels=16)

        with self.assertRaisesRegex(ValueError, "height must be between 1 and 128"):
            ImageMetadata(width=1, height=129, levels=16)

    def test_packet_rejects_corruption(self) -> None:
        raw = bytearray(
            Packet(
                metadata=ImageMetadata(width=32, height=32, levels=16),
                image_id=7,
                fragment_number=0,
                total_fragments=1,
                payload=b"payload",
                flags=FLAG_FIRST_FRAGMENT | FLAG_LAST_FRAGMENT,
            ).to_bytes()
        )
        raw[-1] ^= 0x01

        with self.assertRaises(PacketError):
            Packet.from_bytes(raw)

    def test_fragments_are_reassembled_out_of_order(self) -> None:
        packets = Fragmenter(max_payload_size=3).fragment(
            b"abcdefgh",
            image_id=42,
            metadata=ImageMetadata(width=2, height=2, levels=16),
        )
        reassembler = Reassembler()

        for packet in reversed(packets):
            reassembler.add(packet)

        self.assertTrue(reassembler.is_complete)
        self.assertEqual(reassembler.assemble(), b"abcdefgh")

    def test_reassembler_rejects_inconsistent_metadata(self) -> None:
        first = Fragmenter(max_payload_size=3).fragment(
            b"abcdef",
            image_id=42,
            metadata=ImageMetadata(width=2, height=2, levels=16),
        )[0]
        second = Fragmenter(max_payload_size=3).fragment(
            b"abcdef",
            image_id=42,
            metadata=ImageMetadata(width=4, height=4, levels=16),
        )[1]
        reassembler = Reassembler()
        reassembler.add(first)

        with self.assertRaises(ValueError):
            reassembler.add(second)
