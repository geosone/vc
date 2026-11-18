import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dos_smoke import qemu_cpu


class QemuCpuTest(unittest.TestCase):
    def test_tcg_emulates_a_486(self):
        self.assertEqual(qemu_cpu("tcg"), ["-accel", "tcg", "-cpu", "486"])

    def test_kvm_uses_the_host_cpu(self):
        self.assertEqual(qemu_cpu("kvm"), ["-accel", "kvm", "-cpu", "host"])


if __name__ == "__main__":
    unittest.main()
