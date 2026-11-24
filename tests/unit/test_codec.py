import unittest

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import (
    EncodedImage,
    ImageEncoder,
    ImageEncodingError,
)


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

    def test_encoder_rejects_zero_and_negative_dimensions(self) -> None:
        for width in (0, -1):
            with self.subTest(width=width):
                with self.assertRaisesRegex(
                    ImageEncodingError,
                    "target width.*between 1 and 128",
                ):
                    ImageEncoder(width=width, height=1)

        for height in (0, -1):
            with self.subTest(height=height):
                with self.assertRaisesRegex(
                    ImageEncodingError,
                    "target height.*between 1 and 128",
                ):
                    ImageEncoder(width=1, height=height)

    def test_encoded_image_rejects_zero_and_negative_dimensions(self) -> None:
        for width in (0, -1):
            with self.subTest(width=width):
                with self.assertRaisesRegex(
                    ImageEncodingError,
                    "image width.*between 1 and 128",
                ):
                    EncodedImage(width=width, height=1, levels=16, data=b"")

        for height in (0, -1):
            with self.subTest(height=height):
                with self.assertRaisesRegex(
                    ImageEncodingError,
                    "image height.*between 1 and 128",
                ):
                    EncodedImage(width=1, height=height, levels=16, data=b"")

    def test_encoder_accepts_all_supported_levels(self) -> None:
        expected_sizes = {
            2: 1,
            4: 1,
            8: 1,
            16: 1,
            256: 2,
        }

        for levels, expected_size in expected_sizes.items():
            with self.subTest(levels=levels):
                encoded = ImageEncoder(
                    width=2,
                    height=1,
                    levels=levels,
                ).encode(((0, 255),))

                self.assertEqual(encoded.levels, levels)
                self.assertEqual(len(encoded.data), expected_size)

    def test_encoder_rejects_invalid_pixel_matrices(self) -> None:
        encoder = ImageEncoder(width=2, height=2)
        invalid_matrices = (
            (),
            ((),),
            ((0,), (0, 1)),
            ((-1,),),
            ((256,),),
            (("0",),),
            ((0.0,),),
        )

        for pixels in invalid_matrices:
            with self.subTest(pixels=pixels):
                with self.assertRaises(ImageEncodingError):
                    encoder.encode(pixels)
