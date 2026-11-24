import unittest

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import ImageEncoder, ImageEncodingError


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

    def test_encoder_accepts_independent_dimensions_up_to_128(self) -> None:
        for width, height in ((1, 1), (128, 1), (1, 128), (3, 2), (128, 128)):
            with self.subTest(width=width, height=height):
                encoded = ImageEncoder(width=width, height=height).encode(((255,),))

                self.assertEqual((encoded.width, encoded.height), (width, height))

        self.assertEqual(
            len(ImageEncoder(width=128, height=128).encode(((255,),)).data),
            8192,
        )

    def test_encoder_rejects_dimensions_above_128(self) -> None:
        with self.assertRaisesRegex(ImageEncodingError, "target width.*128"):
            ImageEncoder(width=129, height=1)

        with self.assertRaisesRegex(ImageEncodingError, "target height.*128"):
            ImageEncoder(width=1, height=129)
