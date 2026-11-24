import unittest

from meshmedia_lab.codec.rgb332 import (
    EncodedRgb332Image,
    Rgb332Decoder,
    Rgb332Encoder,
    Rgb332EncodingError,
)
from meshmedia_lab.media import CODEC_RGB332


class Rgb332CodecTests(unittest.TestCase):
    def test_pack_order_is_row_major_rrrgggbb(self) -> None:
        source = (
            ((255, 0, 0), (0, 255, 0)),
            ((0, 0, 255), (255, 255, 255)),
        )

        encoded = Rgb332Encoder(width=2, height=2).encode(source)

        self.assertEqual(encoded.data, bytes((0xE0, 0x1C, 0x03, 0xFF)))

    def test_quantization_uses_floor_boundaries(self) -> None:
        encoder = Rgb332Encoder(width=1, height=1)

        red_values = (
            0,
            31,
            32,
            63,
            64,
            95,
            96,
            127,
            128,
            159,
            160,
            191,
            192,
            223,
            224,
            255,
        )
        red_codes = (0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7)
        for value, code in zip(red_values, red_codes):
            with self.subTest(channel="red", value=value):
                self.assertEqual(
                    encoder.encode((((value, 0, 0),),)).data,
                    bytes((code << 5,)),
                )

        green_values = red_values
        green_codes = red_codes
        for value, code in zip(green_values, green_codes):
            with self.subTest(channel="green", value=value):
                self.assertEqual(
                    encoder.encode((((0, value, 0),),)).data,
                    bytes((code << 2,)),
                )

        blue_values = (0, 63, 64, 127, 128, 191, 192, 255)
        blue_codes = (0, 0, 1, 1, 2, 2, 3, 3)
        for value, code in zip(blue_values, blue_codes):
            with self.subTest(channel="blue", value=value):
                self.assertEqual(
                    encoder.encode((((0, 0, value),),)).data,
                    bytes((code,)),
                )

    def test_decoder_uses_deterministic_reconstruction_levels(self) -> None:
        encoded = EncodedRgb332Image(
            width=5,
            height=1,
            data=bytes((0x00, 0xE0, 0x1C, 0x03, 0xFF)),
        )

        decoded = Rgb332Decoder().decode(encoded)

        self.assertEqual(
            decoded,
            (
                (
                    (0, 0, 0),
                    (255, 0, 0),
                    (0, 255, 0),
                    (0, 0, 255),
                    (255, 255, 255),
                ),
            ),
        )

    def test_encoder_accepts_independent_dimensions(self) -> None:
        source = (
            ((0, 0, 0), (255, 0, 0), (0, 255, 0)),
            ((0, 0, 255), (255, 255, 255), (128, 64, 32)),
        )

        encoded = Rgb332Encoder(width=3, height=2).encode(source)
        decoded = Rgb332Decoder().decode(encoded)

        self.assertEqual((encoded.width, encoded.height), (3, 2))
        self.assertEqual(len(encoded.data), 6)
        self.assertEqual((len(decoded), len(decoded[0])), (2, 3))

    def test_round_trip_has_expected_size_at_32_and_64(self) -> None:
        source = (
            ((0, 0, 0), (255, 0, 0)),
            ((0, 255, 0), (0, 0, 255)),
        )

        for dimension in (32, 64):
            with self.subTest(dimension=dimension):
                encoded = Rgb332Encoder(
                    width=dimension,
                    height=dimension,
                ).encode(source)
                decoded = Rgb332Decoder().decode(encoded)

                self.assertEqual(len(encoded.data), dimension * dimension)
                self.assertEqual(len(decoded), dimension)
                self.assertTrue(all(len(row) == dimension for row in decoded))
                self.assertEqual(decoded[0][0], (0, 0, 0))
                self.assertEqual(decoded[-1][-1], (0, 0, 255))

    def test_encoder_rejects_invalid_pixels(self) -> None:
        encoder = Rgb332Encoder(width=2, height=2)

        invalid_matrices = (
            (),
            ((),),
            (((0, 0),),),
            (((0, 0, 0, 0),),),
            (((256, 0, 0),),),
            (((0, 256, 0),),),
            (((0, 0, 256),),),
            (((0, -1, 0),),),
            ((("0", 0, 0),),),
        )
        for pixels in invalid_matrices:
            with self.subTest(pixels=pixels):
                with self.assertRaises(Rgb332EncodingError):
                    encoder.encode(pixels)

        with self.assertRaisesRegex(Rgb332EncodingError, "same width"):
            encoder.encode((((0, 0, 0),), ((0, 0, 0), (0, 0, 0))))

    def test_encoder_and_encoded_image_reject_non_positive_dimensions(self) -> None:
        for width in (0, -1):
            with self.subTest(width=width):
                with self.assertRaisesRegex(
                    Rgb332EncodingError,
                    "width.*between 1 and 64",
                ):
                    Rgb332Encoder(width=width, height=1)

                with self.assertRaisesRegex(
                    Rgb332EncodingError,
                    "width.*between 1 and 64",
                ):
                    EncodedRgb332Image(width=width, height=1, data=b"")

        for height in (0, -1):
            with self.subTest(height=height):
                with self.assertRaisesRegex(
                    Rgb332EncodingError,
                    "height.*between 1 and 64",
                ):
                    Rgb332Encoder(width=1, height=height)

                with self.assertRaisesRegex(
                    Rgb332EncodingError,
                    "height.*between 1 and 64",
                ):
                    EncodedRgb332Image(width=1, height=height, data=b"")

    def test_encoder_rejects_dimensions_above_64(self) -> None:
        with self.assertRaisesRegex(Rgb332EncodingError, "width.*64"):
            Rgb332Encoder(width=65, height=1)

        with self.assertRaisesRegex(Rgb332EncodingError, "height.*64"):
            Rgb332Encoder(width=1, height=65)

    def test_encoded_image_rejects_truncated_or_extra_data(self) -> None:
        for data in (b"", b"123", b"12345"):
            with self.subTest(data=data):
                with self.assertRaises(Rgb332EncodingError):
                    EncodedRgb332Image(width=2, height=2, data=data)

    def test_encoded_image_accepts_64_by_64(self) -> None:
        encoded = EncodedRgb332Image(
            width=64,
            height=64,
            data=bytes(64 * 64),
        )

        self.assertEqual(len(encoded.data), 4096)

    def test_encoded_image_exposes_rgb332_metadata(self) -> None:
        encoded = EncodedRgb332Image(width=32, height=32, data=bytes(1024))

        self.assertEqual(encoded.metadata.codec, CODEC_RGB332)
        self.assertEqual(encoded.metadata.levels, 0)
