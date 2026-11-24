import unittest

from apps.local.rgb332_transport import (
    Rgb332Datagram,
    Rgb332DatagramError,
    fragment_data,
)


class Rgb332TransportTests(unittest.TestCase):
    def test_datagram_round_trip_is_separate_from_mm1(self) -> None:
        datagram = Rgb332Datagram(
            image_id=38,
            fragment_number=2,
            total_fragments=16,
            width=32,
            height=32,
            payload=b"payload",
        )

        decoded = Rgb332Datagram.from_bytes(datagram.to_bytes())

        self.assertEqual(decoded, datagram)

    def test_fragment_data_counts_32_by_32_rgb332_messages(self) -> None:
        datagrams = fragment_data(
            bytes(32 * 32),
            image_id=38,
            width=32,
            height=32,
            payload_size=64,
        )

        self.assertEqual(len(datagrams), 16)
        self.assertEqual(sum(len(datagram.payload) for datagram in datagrams), 1024)
        self.assertTrue(all(len(datagram.payload) <= 64 for datagram in datagrams))

    def test_datagram_rejects_invalid_length(self) -> None:
        datagram = Rgb332Datagram(
            image_id=38,
            fragment_number=0,
            total_fragments=1,
            width=32,
            height=32,
            payload=b"payload",
        )
        raw = datagram.to_bytes() + b"extra"

        with self.assertRaises(Rgb332DatagramError):
            Rgb332Datagram.from_bytes(raw)
