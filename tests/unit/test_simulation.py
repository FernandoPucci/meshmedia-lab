import unittest

from meshmedia_lab.simulation.channel import ChannelConfig, ChannelSimulator


class ChannelSimulationTests(unittest.TestCase):
    def test_perfect_channel_delivers_all_payloads(self) -> None:
        channel = ChannelSimulator(ChannelConfig(seed=1))

        self.assertEqual(channel.transmit((b"one", b"two")), (b"one", b"two"))

    def test_loss_can_be_configured(self) -> None:
        channel = ChannelSimulator(ChannelConfig(loss_rate=1.0, seed=1))

        self.assertEqual(channel.transmit((b"one", b"two")), ())
