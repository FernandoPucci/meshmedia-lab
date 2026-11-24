import unittest

from meshmedia_lab.application.pipeline import ImagePipeline
from meshmedia_lab.codec.encoder import ImageEncoder
from meshmedia_lab.protocol.fragmenter import Fragmenter


class ImagePipelineTests(unittest.TestCase):
    def test_pipeline_transmits_and_reconstructs_an_image(self) -> None:
        pipeline = ImagePipeline(
            encoder=ImageEncoder(width=2, height=2, levels=16),
            fragmenter=Fragmenter(max_payload_size=1),
        )

        result = pipeline.transmit(
            (
                (0, 128),
                (255, 64),
            ),
            image_id=10,
        )

        self.assertEqual(result.image, ((0, 136), (255, 68)))
        self.assertEqual(result.packets_sent, 2)
        self.assertEqual(result.packets_received, 2)

    def test_pipeline_selects_rgb332_codec(self) -> None:
        pipeline = ImagePipeline(
            fragmenter=Fragmenter(max_payload_size=1),
            codec="rgb332",
            width=2,
            height=2,
        )

        result = pipeline.transmit(
            (
                ((0, 0, 0), (255, 0, 0)),
                ((0, 255, 0), (0, 0, 255)),
            ),
            image_id=11,
        )

        self.assertEqual(
            result.image,
            (
                ((0, 0, 0), (255, 0, 0)),
                ((0, 255, 0), (0, 0, 255)),
            ),
        )
        self.assertEqual(result.encoded_size, 4)
        self.assertEqual(result.packets_sent, 4)
        self.assertEqual(result.packets_received, 4)
