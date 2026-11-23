import unittest

from meshmedia_lab.transport.udp import UdpReceiver, UdpSender


class UdpTransportTests(unittest.TestCase):
    def test_udp_preserves_one_packet_per_datagram(self) -> None:
        with UdpReceiver("127.0.0.1", 0, timeout=1.0) as receiver:
            with UdpSender(*receiver.address) as sender:
                sender.send(b"packet-one")
                payload, address = receiver.receive()

        self.assertEqual(payload, b"packet-one")
        self.assertEqual(address[0], "127.0.0.1")
