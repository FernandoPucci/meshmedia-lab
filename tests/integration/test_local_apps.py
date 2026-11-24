import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised only without the local extra
    Image = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@unittest.skipIf(Image is None, "Pillow is required for local application tests")
class LocalApplicationsTests(unittest.TestCase):
    def test_tx_and_rx_exchange_an_image_over_udp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            input_path = temporary / "input.png"
            output_path = temporary / "received.png"
            image = Image.new("L", (4, 3))
            image.putdata([0, 32, 64, 96, 128, 160, 192, 224, 255, 16, 80, 144])
            image.save(input_path)

            port = self._free_port()
            environment = os.environ.copy()
            environment["PYTHONPATH"] = os.pathsep.join(
                (str(PROJECT_ROOT / "src"), str(PROJECT_ROOT))
            )
            receiver = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "apps.local.rx",
                    "--bind",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--output",
                    str(output_path),
                    "--timeout",
                    "5",
                    "--log-level",
                    "DEBUG",
                ],
                cwd=PROJECT_ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            try:
                ready_line = receiver.stdout.readline() if receiver.stdout else ""
                self.assertIn("RX listening", ready_line)
                transmitter = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "apps.local.tx",
                        "--image",
                        str(input_path),
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--resolution",
                        "8x6",
                        "--levels",
                        "16",
                        "--payload",
                        "3",
                        "--image-id",
                        "11",
                        "--log-level",
                        "DEBUG",
                    ],
                    cwd=PROJECT_ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
                receiver_output, _ = receiver.communicate(timeout=5)
            finally:
                if receiver.poll() is None:
                    receiver.kill()
                    receiver.wait()

            self.assertEqual(transmitter.returncode, 0, transmitter.stderr)
            self.assertEqual(receiver.returncode, 0, receiver_output)
            self.assertTrue(output_path.exists())
            self.assertIn("TX msg=1/8 message_bytes=24", transmitter.stderr)
            self.assertIn("TX msg=8/8", transmitter.stderr)
            self.assertIn("raw:\n", transmitter.stderr)
            self.assertIn("RX msg=1/8 message_bytes=24", receiver_output)
            self.assertIn("messages=8", receiver_output)
            self.assertIn("message_bytes_total=192", receiver_output)

            with Image.open(output_path) as received:
                self.assertEqual(received.mode, "L")
                self.assertEqual(received.size, (8, 6))

    def test_tx_and_rx_exchange_rgb332_over_udp(self) -> None:
        self._assert_rgb332_exchange(
            resolution="32x32",
            image_id=12,
            expected_messages=16,
            expected_size=(32, 32),
        )

    def test_tx_and_rx_exchange_rgb332_64_by_64_over_udp(self) -> None:
        self._assert_rgb332_exchange(
            resolution="64x64",
            image_id=13,
            expected_messages=64,
            expected_size=(64, 64),
        )

    def _assert_rgb332_exchange(
        self,
        *,
        resolution: str,
        image_id: int,
        expected_messages: int,
        expected_size: tuple[int, int],
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            input_path = temporary / "input.png"
            output_path = temporary / "received.png"
            image = Image.new("RGB", (4, 3))
            image.putdata(
                [
                    (0, 0, 0),
                    (255, 0, 0),
                    (0, 255, 0),
                    (0, 0, 255),
                    (255, 255, 255),
                    (128, 64, 32),
                    (32, 64, 128),
                    (200, 100, 50),
                    (50, 100, 200),
                    (16, 32, 48),
                    (64, 96, 128),
                    (192, 224, 240),
                ]
            )
            image.save(input_path)

            port = self._free_port()
            environment = os.environ.copy()
            environment["PYTHONPATH"] = os.pathsep.join(
                (str(PROJECT_ROOT / "src"), str(PROJECT_ROOT))
            )
            receiver = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "apps.local.rx",
                    "--bind",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--output",
                    str(output_path),
                    "--timeout",
                    "5",
                    "--log-level",
                    "DEBUG",
                ],
                cwd=PROJECT_ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            try:
                ready_line = receiver.stdout.readline() if receiver.stdout else ""
                self.assertIn("RX listening", ready_line)
                transmitter = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "apps.local.tx",
                        "--image",
                        str(input_path),
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--resolution",
                        resolution,
                        "--codec",
                        "rgb332",
                        "--payload",
                        "64",
                        "--image-id",
                        str(image_id),
                        "--log-level",
                        "DEBUG",
                    ],
                    cwd=PROJECT_ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
                receiver_output, _ = receiver.communicate(timeout=5)
            finally:
                if receiver.poll() is None:
                    receiver.kill()
                    receiver.wait()

            self.assertEqual(transmitter.returncode, 0, transmitter.stderr)
            self.assertEqual(receiver.returncode, 0, receiver_output)
            self.assertTrue(output_path.exists())
            self.assertIn("codec=rgb332", transmitter.stderr)
            self.assertIn("codec=0x02", transmitter.stderr)
            self.assertIn("levels=0", transmitter.stderr)
            self.assertIn(f"messages={expected_messages}", transmitter.stderr)
            self.assertIn(f"messages={expected_messages}", receiver_output)
            expected_wire_bytes = (
                expected_size[0] * expected_size[1] + expected_messages * 21
            )
            self.assertIn(
                f"message_bytes_total={expected_wire_bytes}",
                transmitter.stderr,
            )
            self.assertIn("codec=0x02", receiver_output)
            self.assertIn("levels=0", receiver_output)

            with Image.open(output_path) as received:
                self.assertEqual(received.mode, "RGB")
                self.assertEqual(received.size, expected_size)

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind(("127.0.0.1", 0))
            return probe.getsockname()[1]
