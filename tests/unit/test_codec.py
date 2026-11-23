import unittest

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import ImageEncoder


class ImageCodecTests(unittest.TestCase):
    def test_round_trip_preserves_dimensions_and_quantized_values(self) -> None:
        source = (
            (0, 128),
            (255, 64),
        )

        encoded = ImageEncoder(width=2, height=2, levels=16).encode(source)
        decoded = ImageDecoder().decode(encoded)

        self.assertEqual((encoded.width, encoded.height), (2, 2))
        self.assertEqual(decoded, ((0, 136), (255, 68)))

    def test_encoder_resizes_to_target_dimensions(self) -> None:
        encoded = ImageEncoder(width=4, height=4).encode(((255,),))

        self.assertEqual((encoded.width, encoded.height), (4, 4))
        self.assertEqual(len(encoded.data), 8)
