import unittest

from meshmedia_lab.protocol.crc import crc16
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.protocol.packet import Packet, PacketError
from meshmedia_lab.protocol.reassembler import Reassembler


class ProtocolTests(unittest.TestCase):
    def test_crc_matches_ccitt_false_reference_vector(self) -> None:
        self.assertEqual(crc16(b"123456789"), 0x29B1)

    def test_packet_round_trip(self) -> None:
        packet = Packet(
            image_id=7,
            fragment_number=0,
            total_fragments=1,
            payload=b"payload",
        )

        self.assertEqual(Packet.from_bytes(packet.to_bytes()), packet)

    def test_packet_rejects_corruption(self) -> None:
        raw = bytearray(
            Packet(
                image_id=7,
                fragment_number=0,
                total_fragments=1,
                payload=b"payload",
            ).to_bytes()
        )
        raw[-1] ^= 0x01

        with self.assertRaises(PacketError):
            Packet.from_bytes(raw)

    def test_fragments_are_reassembled_out_of_order(self) -> None:
        packets = Fragmenter(max_payload_size=3).fragment(
            b"abcdefgh", image_id=42
        )
        reassembler = Reassembler()

        for packet in reversed(packets):
            reassembler.add(packet)

        self.assertTrue(reassembler.is_complete)
        self.assertEqual(reassembler.assemble(), b"abcdefgh")
