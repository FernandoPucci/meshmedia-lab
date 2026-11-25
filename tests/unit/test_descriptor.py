from dataclasses import replace
import random
import unittest

from meshmedia_lab.media import CODEC_RGB332, ImageMetadata
from meshmedia_lab.protocol.descriptor import DescriptorError, TransmissionDescriptor
from meshmedia_lab.protocol.fragmenter import FragmentationError, Fragmenter
from meshmedia_lab.protocol.packet import FLAG_INLINE_DESCRIPTOR, Packet, PacketError
from meshmedia_lab.protocol.reassembler import Reassembler, ReassemblyError


GRAY_PREFIX = bytes.fromhex(
    "54 44 10 01 00 01 01 00 02 00 02 00 10 00 00 00 02 00 00"
)
RGB_PREFIX = bytes.fromhex(
    "54 44 10 01 00 01 02 00 02 00 01 00 00 00 00 00 02 00 00"
)


class DescriptorTests(unittest.TestCase):
    def test_fixed_prefix_vectors(self) -> None:
        for raw, metadata in (
            (GRAY_PREFIX, ImageMetadata(2, 2, 16)),
            (RGB_PREFIX, ImageMetadata(2, 1, 0, codec=CODEC_RGB332)),
        ):
            with self.subTest(codec=metadata.codec):
                descriptor = TransmissionDescriptor(metadata, encoded_length=2)
                self.assertEqual(descriptor.to_bytes(), raw)
                self.assertEqual(TransmissionDescriptor.from_bytes(raw), descriptor)
                self.assertEqual(
                    TransmissionDescriptor.from_payload(raw + b"TD"),
                    (descriptor, b"TD"),
                )
                with self.assertRaises(DescriptorError):
                    TransmissionDescriptor.from_bytes(raw + b"extra")

    def test_every_truncation_is_rejected(self) -> None:
        for end in range(len(GRAY_PREFIX)):
            with self.subTest(end=end):
                with self.assertRaises(DescriptorError):
                    TransmissionDescriptor.from_payload(GRAY_PREFIX[:end])

    def test_invalid_fields_are_rejected(self) -> None:
        # Offsets are relative to the complete prefix, not to the body.
        mutations = (
            (0, b"X"), (1, b"X"),                         # marker
            (2, b"\x00"), (2, b"\x0f"), (2, b"\x11"), (2, b"\xff"),
            (3, b"\x02"), (4, b"\x01"),                   # version, flags
            (5, b"\x02"), (6, b"\xff"),                   # media, codec
            (7, b"\x00\x00"), (7, b"\x00\x81"),           # width
            (9, b"\x00\x00"), (9, b"\xff\xff"),           # height
            (11, b"\x00\x20"), (11, b"\x00\x00"),         # levels
            (13, b"\x00\x00\x00\x00"),
            (13, b"\x00\x00\x00\x03"), (13, b"\xff\xff\xff\xff"),
            (17, b"\x01"), (18, b"\x01"),                 # compression, extras
        )
        for offset, value in mutations:
            with self.subTest(offset=offset, value=value):
                invalid = bytearray(GRAY_PREFIX)
                invalid[offset:offset + len(value)] = value
                with self.assertRaises(DescriptorError):
                    TransmissionDescriptor.from_payload(invalid)

    def test_rgb332_limits_and_levels_are_checked_during_parsing(self) -> None:
        for offset, value in (
            (7, b"\x00\x41"), (9, b"\x00\x41"), (11, b"\x00\x10"),
        ):
            with self.subTest(offset=offset):
                invalid = bytearray(RGB_PREFIX)
                invalid[offset:offset + len(value)] = value
                with self.assertRaises(DescriptorError):
                    TransmissionDescriptor.from_payload(invalid)

    def test_duplicated_body_and_oversized_payload_are_rejected(self) -> None:
        duplicated = b"TD\x20" + GRAY_PREFIX[3:] * 2
        for invalid in (duplicated, GRAY_PREFIX + bytes(256)):
            with self.subTest(size=len(invalid)):
                with self.assertRaises(DescriptorError):
                    TransmissionDescriptor.from_payload(invalid)

    def test_construction_is_as_strict_as_parsing(self) -> None:
        descriptor = TransmissionDescriptor(ImageMetadata(2, 2, 16), 2)
        for changes in (
            {"version": 2}, {"flags": 1}, {"compression_id": 1},
            {"codec_parameters": b"extra"}, {"encoded_length": -1},
            {"encoded_length": 0x100000000}, {"encoded_length": 2.0},
            {"metadata": ImageMetadata(2, 2, 16, codec=0xFF)},
            {"metadata": ImageMetadata(2, 2, 32)},
            {"metadata": ImageMetadata(2, 2, 16, version=2)},
            {"metadata": ImageMetadata(65, 1, 0, codec=CODEC_RGB332)},
            {"metadata": ImageMetadata(2, 2, 16, media_type=2)},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(DescriptorError):
                    replace(descriptor, **changes)
        for invalid in (19, None, "TD"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(DescriptorError):
                    TransmissionDescriptor.from_payload(invalid)

    def test_bytes_like_input_is_bounded_by_bytes_not_element_count(self) -> None:
        self.assertEqual(
            TransmissionDescriptor.from_bytes(memoryview(GRAY_PREFIX)),
            TransmissionDescriptor(ImageMetadata(2, 2, 16), 2),
        )
        # 64 integer elements, but 256 bytes: reject before copying the view.
        with self.assertRaisesRegex(DescriptorError, "payload size"):
            TransmissionDescriptor.from_payload(memoryview(bytes(256)).cast("I"))

    def test_supported_levels_and_dimension_boundaries(self) -> None:
        for width, height in ((1, 1), (128, 1), (1, 128), (128, 128)):
            for levels in (2, 4, 8, 16, 256):
                with self.subTest(width=width, height=height, levels=levels):
                    length = (width * height * (levels.bit_length() - 1) + 7) // 8
                    descriptor = TransmissionDescriptor(
                        ImageMetadata(width, height, levels), length
                    )
                    self.assertEqual(
                        TransmissionDescriptor.from_bytes(descriptor.to_bytes()),
                        descriptor,
                    )
        for width, height in ((1, 1), (64, 1), (1, 64), (64, 64)):
            with self.subTest(width=width, height=height):
                descriptor = TransmissionDescriptor(
                    ImageMetadata(width, height, 0, codec=CODEC_RGB332),
                    width * height,
                )
                self.assertEqual(
                    TransmissionDescriptor.from_bytes(descriptor.to_bytes()), descriptor
                )


class DescriptorTransmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = ImageMetadata(2, 2, 16)
        self.data = b"\x08\xf4"
        self.descriptor = TransmissionDescriptor(self.metadata, 2)

    def _packets(self, payload_size: int = 20) -> tuple[Packet, ...]:
        return Fragmenter(payload_size).fragment(
            self.data, image_id=7, metadata=self.metadata, descriptor=self.descriptor
        )

    def test_fixed_packet_vectors_preserve_header_and_crc(self) -> None:
        legacy = Fragmenter(64).fragment(
            self.data, image_id=7, metadata=self.metadata
        )[0]
        extended = self._packets(64)[0]
        self.assertEqual(
            legacy.to_bytes(),
            bytes.fromhex(
                "4d 4d 01 01 01 03 00 07 00 00 00 01 00 02 00 02 00 10 "
                "02 08 f4 2c ee"
            ),
        )
        self.assertEqual(
            extended.to_bytes(),
            bytes.fromhex(
                "4d 4d 01 01 01 07 00 07 00 00 00 01 00 02 00 02 00 10 15 "
                "54 44 10 01 00 01 01 00 02 00 02 00 10 00 00 00 02 00 00 "
                "08 f4 b7 23"
            ),
        )
        self.assertEqual(Packet.from_bytes(extended.to_bytes()), extended)
        self.assertTrue(extended.flags & FLAG_INLINE_DESCRIPTOR)
        self.assertEqual(len(extended.to_bytes()) - len(extended.payload), 21)

    def test_legacy_rgb332_and_fragmented_grayscale_fixed_vectors(self) -> None:
        rgb = Fragmenter().fragment(
            b"\xe0\x1c", image_id=7,
            metadata=ImageMetadata(2, 1, 0, codec=CODEC_RGB332),
        )
        self.assertEqual(
            rgb[0].to_bytes(),
            bytes.fromhex(
                "4d 4d 01 01 02 03 00 07 00 00 00 01 00 02 00 01 00 00 "
                "02 e0 1c 2d b2"
            ),
        )
        gray = Fragmenter(1).fragment(
            self.data, image_id=7, metadata=self.metadata
        )
        self.assertEqual(
            tuple(packet.to_bytes() for packet in gray),
            tuple(bytes.fromhex(vector) for vector in (
                "4d 4d 01 01 01 01 00 07 00 00 00 02 00 02 00 02 00 10 01 08 ed 07",
                "4d 4d 01 01 01 02 00 07 00 01 00 02 00 02 00 02 00 10 01 f4 f8 f8",
            )),
        )

    def test_fragmentation_and_reassembly_at_payload_boundaries(self) -> None:
        for payload_size in (19, 20, 21, 64, 255):
            with self.subTest(payload_size=payload_size):
                packets = self._packets(payload_size)
                self.assertEqual(
                    [packet.flags for packet in packets],
                    [7] if len(packets) == 1 else [5, 6],
                )
                self.assertTrue(all(len(p.payload) <= payload_size for p in packets))
                self.assertEqual(
                    b"".join(p.payload for p in packets), GRAY_PREFIX + self.data
                )
                receiver = Reassembler()
                for packet in reversed(packets):
                    receiver.add(Packet.from_bytes(packet.to_bytes()))
                self.assertTrue(receiver.is_complete)
                self.assertEqual(receiver.descriptor, self.descriptor)
                self.assertEqual(receiver.metadata, self.descriptor.metadata)
                self.assertEqual(receiver.assemble(), self.data)

    def test_tx_rejects_small_payload_and_inconsistent_inputs(self) -> None:
        for payload_size in (1, 18):
            with self.subTest(payload_size=payload_size):
                with self.assertRaisesRegex(FragmentationError, "cannot fit"):
                    self._packets(payload_size)
        with self.assertRaisesRegex(FragmentationError, "metadata differ"):
            Fragmenter().fragment(
                self.data, image_id=7, metadata=ImageMetadata(1, 2, 16),
                descriptor=self.descriptor,
            )
        with self.assertRaisesRegex(FragmentationError, "length"):
            Fragmenter().fragment(
                b"\x08", image_id=7, metadata=self.metadata, descriptor=self.descriptor
            )

    def test_marker_collision_is_ordinary_legacy_data(self) -> None:
        packets = Fragmenter(64).fragment(
            b"TD", image_id=7, metadata=self.metadata
        )
        receiver = Reassembler()
        receiver.add(Packet.from_bytes(packets[0].to_bytes()))
        self.assertIsNone(receiver.descriptor)
        self.assertEqual(receiver.assemble(), b"TD")

    def test_marker_in_later_fragment_is_not_parsed(self) -> None:
        descriptor = TransmissionDescriptor(ImageMetadata(4, 1, 256), 4)
        packets = Fragmenter(21).fragment(
            b"\x00\x00TD", image_id=7, metadata=descriptor.metadata,
            descriptor=descriptor,
        )
        self.assertEqual(packets[1].payload, b"TD")
        receiver = Reassembler()
        for packet in packets:
            receiver.add(packet)
        self.assertEqual(receiver.assemble(), b"\x00\x00TD")

    def test_first_fragment_absence_prevents_completion(self) -> None:
        receiver = Reassembler()
        receiver.add(self._packets()[1])
        self.assertFalse(receiver.is_complete)
        self.assertIsNone(receiver.descriptor)
        self.assertEqual(receiver.missing_fragments, (0,))
        with self.assertRaises(ReassemblyError):
            receiver.assemble()

    def test_identical_duplicates_do_not_count_twice(self) -> None:
        receiver = Reassembler()
        packets = self._packets()
        for packet in packets + packets:
            receiver.add(packet)
        self.assertTrue(receiver.is_complete)
        self.assertEqual(receiver.assemble(), self.data)

    def test_conflicting_duplicate_is_terminal(self) -> None:
        receiver = Reassembler()
        packets = self._packets()
        receiver.add(packets[0])
        invalid = replace(packets[0], payload=GRAY_PREFIX + b"\xff")
        with self.assertRaisesRegex(ReassemblyError, "duplicate"):
            receiver.add(invalid)
        self.assertTrue(receiver.rejected)
        self.assertFalse(receiver.is_complete)
        with self.assertRaises(ReassemblyError):
            receiver.add(packets[1])
        with self.assertRaises(ReassemblyError):
            receiver.assemble()

    def test_invalid_descriptor_cannot_fall_back_to_legacy(self) -> None:
        first = self._packets()[0]
        for payload in (b"X" + first.payload[1:], first.payload[:10]):
            with self.subTest(payload=payload):
                receiver = Reassembler()
                with self.assertRaises(ReassemblyError):
                    receiver.add(replace(first, payload=payload))
                self.assertTrue(receiver.rejected)
                with self.assertRaises(ReassemblyError):
                    receiver.assemble()

    def test_descriptor_and_header_must_match(self) -> None:
        first = self._packets()[0]
        other = TransmissionDescriptor(ImageMetadata(4, 1, 16), 2)
        receiver = Reassembler()
        with self.assertRaisesRegex(ReassemblyError, "metadata differ"):
            receiver.add(replace(first, payload=other.to_bytes() + b"\x08"))

    def test_inconsistent_modes_metadata_counts_and_flags_are_rejected(self) -> None:
        first, last = self._packets()
        for invalid in (
            replace(last, flags=2),
            replace(last, flags=7),
            replace(last, flags=0x86),
            replace(last, metadata=ImageMetadata(1, 2, 16)),
            replace(last, total_fragments=3, flags=4),
            replace(last, payload=b""),
        ):
            with self.subTest(packet=invalid):
                receiver = Reassembler()
                receiver.add(first)
                with self.assertRaises(ReassemblyError):
                    receiver.add(invalid)
                self.assertTrue(receiver.rejected)
                self.assertEqual(receiver.missing_fragments, ())
        receiver = Reassembler()
        receiver.add(replace(first, flags=1))  # explicit legacy
        with self.assertRaisesRegex(ReassemblyError, "mode"):
            receiver.add(last)
        self.assertTrue(receiver.rejected)

    def test_header_bounds_apply_before_first_fragment(self) -> None:
        last = self._packets()[1]
        for invalid in (
            replace(last, total_fragments=65535, flags=4),
            replace(last, payload=bytes(3)),
            replace(last, metadata=ImageMetadata(65, 1, 0, codec=CODEC_RGB332)),
            replace(last, metadata=ImageMetadata(2, 2, 32)),
            replace(last, metadata=ImageMetadata(2, 2, 16, codec=255)),
            replace(last, metadata=ImageMetadata(2, 2, 16, version=2)),
        ):
            with self.subTest(packet=invalid):
                receiver = Reassembler()
                with self.assertRaises(ReassemblyError):
                    receiver.add(invalid)
                self.assertTrue(receiver.rejected)
                self.assertEqual(receiver.missing_fragments, ())

    def test_final_data_length_must_match_exactly(self) -> None:
        single = self._packets(64)[0]
        for payload in (GRAY_PREFIX + self.data[:1], single.payload + b"\xff"):
            with self.subTest(payload=payload):
                receiver = Reassembler()
                with self.assertRaises(ReassemblyError):
                    receiver.add(replace(single, payload=payload))
                self.assertFalse(receiver.is_complete)
        first, last = self._packets()
        receiver = Reassembler()
        receiver.add(last)
        with self.assertRaisesRegex(ReassemblyError, "shorter"):
            receiver.add(replace(first, payload=GRAY_PREFIX))

    def test_other_image_does_not_poison_current_transmission(self) -> None:
        first, last = self._packets()
        receiver = Reassembler()
        receiver.add(first)
        with self.assertRaises(ReassemblyError):
            receiver.add(replace(last, image_id=8))
        self.assertFalse(receiver.rejected)
        receiver.add(last)
        self.assertTrue(receiver.is_complete)

    def test_crc_still_covers_descriptor_bytes(self) -> None:
        raw = bytearray(self._packets(64)[0].to_bytes())
        raw[22] ^= 1  # descriptor version, after header/marker/length
        with self.assertRaisesRegex(PacketError, "CRC"):
            Packet.from_bytes(raw)

    def test_middle_flags_and_documented_64_byte_cost(self) -> None:
        for metadata, size, count in (
            (ImageMetadata(32, 32, 16), 512, 9),
            (ImageMetadata(32, 32, 0, codec=CODEC_RGB332), 1024, 17),
            (ImageMetadata(64, 64, 0, codec=CODEC_RGB332), 4096, 65),
        ):
            with self.subTest(metadata=metadata):
                packets = Fragmenter().fragment(
                    bytes(size), image_id=7, metadata=metadata,
                    descriptor=TransmissionDescriptor(metadata, size),
                )
                self.assertEqual(len(packets), count)
                self.assertEqual(packets[0].flags, 5)
                self.assertEqual(packets[-1].flags, 6)
                self.assertTrue(all(p.flags == 4 for p in packets[1:-1]))
                self.assertEqual(
                    sum(len(p.to_bytes()) for p in packets), size + 19 + 21 * count
                )

    def test_seeded_permutations_reassemble_both_codecs(self) -> None:
        rng = random.Random(17)
        for codec in (1, 2):
            for scenario in range(20):
                width, height = rng.randint(1, 64), rng.randint(1, 64)
                levels = rng.choice((2, 4, 8, 16, 256)) if codec == 1 else 0
                metadata = ImageMetadata(width, height, levels, codec=codec)
                size = (
                    (width * height * (levels.bit_length() - 1) + 7) // 8
                    if codec == 1 else width * height
                )
                data = rng.randbytes(size)
                with self.subTest(codec=codec, scenario=scenario):
                    packets = list(Fragmenter(rng.randint(19, 255)).fragment(
                        data, image_id=17, metadata=metadata,
                        descriptor=TransmissionDescriptor(metadata, size),
                    ))
                    packets += packets[:2]  # duplicates before/after fragment zero
                    rng.shuffle(packets)
                    receiver = Reassembler()
                    for packet in packets:
                        receiver.add(Packet.from_bytes(packet.to_bytes()))
                    self.assertTrue(receiver.is_complete)
                    self.assertEqual(receiver.assemble(), data)
