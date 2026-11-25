import unittest

from meshmedia_lab.application.pipeline import ImagePipeline, TransmissionError
from meshmedia_lab.codec.encoder import ImageEncoder
from meshmedia_lab.fec import (
    FecConfig,
    IncompleteBlockPolicy,
    PaddingPolicy,
    ReedSolomonDecoder,
    ReedSolomonEncoder,
)
from meshmedia_lab.protocol.fragmenter import Fragmenter


class ImagePipelineTests(unittest.TestCase):
    @staticmethod
    def _fec_config(
        data_symbols: int = 4,
        repair_symbols: int = 3,
    ) -> FecConfig:
        return FecConfig(
            algorithm_id="reed_solomon",
            symbol_size=1,
            data_symbols=data_symbols,
            repair_symbols=repair_symbols,
            block_symbols=data_symbols + repair_symbols,
            interleaving_depth=0,
            padding_policy=PaddingPolicy.ZERO_PAD,
            incomplete_block_policy=IncompleteBlockPolicy.PAD_TO_K,
        )

    @staticmethod
    def _drop_fragments(dropped: set[int]):
        class DropFragments:
            def transmit(self, payloads):
                return tuple(
                    payload
                    for index, payload in enumerate(payloads)
                    if index not in dropped
                )

        return DropFragments()

    def test_descriptor_mode_preserves_both_codec_reconstructions(self) -> None:
        sources = {
            "grayscale": ((0, 128), (255, 64)),
            "rgb332": (
                ((0, 0, 0), (255, 0, 0)),
                ((0, 255, 0), (0, 0, 255)),
            ),
        }
        for codec, source in sources.items():
            with self.subTest(codec=codec):
                legacy = ImagePipeline(codec=codec, width=2, height=2).transmit(source)
                extended = ImagePipeline(
                    codec=codec, width=2, height=2, transmission_mode="descriptor"
                ).transmit(source)
        self.assertEqual(extended.image, legacy.image)
        self.assertEqual(extended.encoded_size, legacy.encoded_size)
        self.assertEqual(extended.packets_sent, extended.packets_received)
        self.assertIsNone(extended.fec_transmission)

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

    def test_grayscale_fec_recovers_source_after_symbol_losses(self) -> None:
        pipeline = ImagePipeline(
            codec="grayscale",
            width=4,
            height=4,
            levels=16,
            fragmenter=Fragmenter(max_payload_size=64),
            fec_encoder=ReedSolomonEncoder(),
            fec_decoder=ReedSolomonDecoder(),
            fec_config=self._fec_config(),
        )
        source = tuple(
            tuple((x + y) * 16 for x in range(4))
            for y in range(4)
        )

        result = pipeline.transmit(
            source,
            image_id=20,
            channel=self._drop_fragments({6, 13}),
        )

        self.assertEqual(result.image, pipeline.decoder.decode(
            pipeline.encoder.encode(source)
        ))
        self.assertEqual(result.encoded_size, 8)
        self.assertEqual(result.packets_sent, 14)
        self.assertEqual(result.packets_received, 12)
        self.assertIsNotNone(result.fec_transmission)
        self.assertEqual(result.fec_transmission.total_blocks, 2)
        self.assertEqual(result.fec_transmission.repair_symbol_count, 6)

    def test_rgb332_fec_recovers_multiple_blocks(self) -> None:
        pipeline = ImagePipeline(
            codec="rgb332",
            width=4,
            height=4,
            fragmenter=Fragmenter(max_payload_size=64),
            fec_encoder=ReedSolomonEncoder(),
            fec_decoder=ReedSolomonDecoder(),
            fec_config=self._fec_config(),
        )
        source = (
            ((0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)),
            ((255, 255, 255), (128, 64, 32), (32, 64, 128), (200, 100, 50)),
            ((50, 100, 200), (16, 32, 48), (64, 96, 128), (192, 224, 240)),
            ((10, 20, 30), (40, 50, 60), (70, 80, 90), (100, 110, 120)),
        )

        result = pipeline.transmit(
            source,
            image_id=21,
            channel=self._drop_fragments({6, 13, 20, 27}),
        )

        self.assertEqual(result.image, pipeline.decoder.decode(
            pipeline.encoder.encode(source)
        ))
        self.assertEqual(result.packets_sent, 28)
        self.assertEqual(result.packets_received, 24)
        self.assertEqual(result.fec_transmission.total_blocks, 4)

    def test_fec_configuration_matrix_is_explicit(self) -> None:
        source = tuple(
            tuple((x * 17 + y * 9) % 256 for x in range(16))
            for y in range(16)
        )
        for data_symbols, repair_symbols in ((28, 4), (24, 8), (20, 12)):
            with self.subTest(
                data_symbols=data_symbols,
                repair_symbols=repair_symbols,
            ):
                pipeline = ImagePipeline(
                    codec="grayscale",
                    width=16,
                    height=16,
                    levels=16,
                    fragmenter=Fragmenter(max_payload_size=64),
                    fec_encoder=ReedSolomonEncoder(),
                    fec_decoder=ReedSolomonDecoder(),
                    fec_config=self._fec_config(
                        data_symbols,
                        repair_symbols,
                    ),
                )
                result = pipeline.transmit(source, image_id=22)
                self.assertEqual(result.image, pipeline.decoder.decode(
                    pipeline.encoder.encode(source)
                ))
                self.assertEqual(
                    result.fec_transmission.config.data_symbols,
                    data_symbols,
                )
                self.assertEqual(
                    result.fec_transmission.config.repair_symbols,
                    repair_symbols,
                )

    def test_fec_preserves_the_optional_descriptor_mode(self) -> None:
        pipeline = ImagePipeline(
            codec="grayscale",
            width=4,
            height=4,
            levels=16,
            transmission_mode="descriptor",
            fragmenter=Fragmenter(max_payload_size=144),
            fec_encoder=ReedSolomonEncoder(),
            fec_decoder=ReedSolomonDecoder(),
            fec_config=self._fec_config(),
        )
        source = tuple(tuple((x + y) * 16 for x in range(4)) for y in range(4))

        result = pipeline.transmit(source, image_id=24)

        self.assertEqual(result.image, pipeline.decoder.decode(
            pipeline.encoder.encode(source)
        ))
        self.assertEqual(result.packets_sent, 14)

    def test_fec_reports_failure_when_a_block_has_too_many_losses(self) -> None:
        pipeline = ImagePipeline(
            codec="grayscale",
            width=4,
            height=4,
            levels=16,
            fragmenter=Fragmenter(max_payload_size=64),
            fec_encoder=ReedSolomonEncoder(),
            fec_decoder=ReedSolomonDecoder(),
            fec_config=self._fec_config(),
        )
        source = tuple(tuple((x + y) * 16 for x in range(4)) for y in range(4))

        with self.assertRaisesRegex(TransmissionError, "missing symbols"):
            pipeline.transmit(
                source,
                image_id=23,
                channel=self._drop_fragments({0, 1, 2, 3}),
            )
