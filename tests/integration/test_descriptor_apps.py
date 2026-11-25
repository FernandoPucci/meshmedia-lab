from contextlib import contextmanager
from dataclasses import replace
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import ImageEncoder
from meshmedia_lab.codec.rgb332 import Rgb332Decoder, Rgb332Encoder
from meshmedia_lab.protocol.descriptor import TransmissionDescriptor
from meshmedia_lab.protocol.fragmenter import Fragmenter

try:
    from PIL import Image
except ImportError:
    Image = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@unittest.skipIf(Image is None, "Pillow is required for local application tests")
class DescriptorApplicationsTests(unittest.TestCase):
    @contextmanager
    def _receiver(self, output_path: Path, timeout: str = "2"):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            (str(PROJECT_ROOT / "src"), str(PROJECT_ROOT))
        )
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        with subprocess.Popen(
            [
                sys.executable, "-m", "apps.local.rx",
                "--bind", "127.0.0.1", "--port", str(port),
                "--output", str(output_path), "--timeout", timeout,
                "--log-level", "INFO",
            ],
            cwd=PROJECT_ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
        ) as receiver:
            try:
                self.assertIn("RX listening", receiver.stdout.readline())
                yield receiver, port, environment
            finally:
                if receiver.poll() is None:
                    receiver.kill()
                receiver.communicate(timeout=5)

    def test_tx_rx_descriptor_reconstructs_both_codecs_exactly(self) -> None:
        gray_source = ((0, 128), (255, 64))
        rgb_source = (((0, 0, 0), (255, 0, 0)), ((0, 255, 0), (0, 0, 255)))
        for codec, width, height in (
            ("grayscale", 3, 2),
            ("grayscale", 128, 128),
            ("rgb332", 32, 32),
            ("rgb332", 64, 64),
        ):
            with self.subTest(codec=codec, width=width, height=height):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    input_path = root / "input.png"
                    output_path = root / "received.png"
                    source = gray_source if codec == "grayscale" else rgb_source
                    image = Image.new("L" if codec == "grayscale" else "RGB", (2, 2))
                    image.putdata([pixel for row in source for pixel in row])
                    image.save(input_path)
                    encoder = (
                        ImageEncoder(width, height, 16)
                        if codec == "grayscale" else Rgb332Encoder(width, height)
                    )
                    decoder = ImageDecoder() if codec == "grayscale" else Rgb332Decoder()
                    encoded = encoder.encode(source)
                    expected = decoder.decode(encoded)
                    # Larger payload keeps the max grayscale case a small UDP smoke test.
                    payload_size = 144 if width == 128 else 64
                    packet_count = (len(encoded.data) + 19 + payload_size - 1) // payload_size
                    with self._receiver(output_path) as (receiver, port, environment):
                        transmitter = subprocess.run(
                            [
                                sys.executable, "-m", "apps.local.tx",
                                "--image", str(input_path), "--host", "127.0.0.1",
                                "--port", str(port), "--codec", codec,
                                "--resolution", f"{width}x{height}", "--payload",
                                str(payload_size), "--transmission-mode", "descriptor",
                            ],
                            cwd=PROJECT_ROOT, env=environment, capture_output=True,
                            text=True, timeout=5, check=False,
                        )
                        receiver_output, _ = receiver.communicate(timeout=5)
                    self.assertEqual(transmitter.returncode, 0, transmitter.stderr)
                    self.assertEqual(receiver.returncode, 0, receiver_output)
                    self.assertIn("mode=descriptor", transmitter.stderr)
                    self.assertIn("mode=descriptor", receiver_output)
                    self.assertIn(f"messages={packet_count}\n", receiver_output)
                    self.assertIn("descriptor_bytes=19", receiver_output)
                    self.assertIn("invalid_packets=0", receiver_output)
                    self.assertNotIn("Logging error", receiver_output + transmitter.stderr)
                    with Image.open(output_path) as received:
                        self.assertEqual(received.mode, image.mode)
                        self.assertEqual(received.size, (width, height))
                        self.assertEqual(
                            list(received.getdata()),
                            [pixel for row in expected for pixel in row],
                        )

    def test_invalid_descriptor_never_creates_an_image(self) -> None:
        encoded = ImageEncoder(2, 2, 16).encode(((0, 128), (255, 64)))
        valid = Fragmenter().fragment(
            encoded.data, image_id=17, metadata=encoded.metadata,
            descriptor=TransmissionDescriptor(encoded.metadata, len(encoded.data)),
        )[0]
        invalid_payloads = (
            b"XX" + valid.payload[2:],
            valid.payload[:10],
            valid.payload[:3] + b"\x02" + valid.payload[4:],
            valid.payload[:6] + b"\xff" + valid.payload[7:],
            valid.payload[:-1],
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as temporary:
                    output_path = Path(temporary) / "invalid.png"
                    with self._receiver(output_path) as (receiver, port, _):
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                            # CRC is recomputed, exercising semantic rejection, not CRC.
                            sender.sendto(
                                replace(valid, payload=payload).to_bytes(),
                                ("127.0.0.1", port),
                            )
                        output, _ = receiver.communicate(timeout=5)
                    self.assertEqual(receiver.returncode, 1, output)
                    self.assertIn("RX rejected packet", output)
                    self.assertNotIn("Traceback", output)
                    self.assertFalse(output_path.exists())

    def test_missing_first_fragment_times_out_without_output(self) -> None:
        encoded = ImageEncoder(2, 2, 16).encode(((0, 128), (255, 64)))
        packets = Fragmenter(19).fragment(
            encoded.data, image_id=17, metadata=encoded.metadata,
            descriptor=TransmissionDescriptor(encoded.metadata, len(encoded.data)),
        )
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "missing.png"
            with self._receiver(output_path, timeout="0.2") as (receiver, port, _):
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                    sender.sendto(packets[1].to_bytes(), ("127.0.0.1", port))
                output, _ = receiver.communicate(timeout=5)
            self.assertEqual(receiver.returncode, 1, output)
            self.assertIn("timeout", output)
            self.assertFalse(output_path.exists())
