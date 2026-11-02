"""Hardware-independent tests of the Zigbee2MQTT startup grace gate."""
import unittest

from custom_components.adaptive_alarm.engine.siren_startup import (
    STARTUP_SIREN_GRACE_SECONDS,
    SirenStartupOffGate,
)


class SirenStartupGateTests(unittest.TestCase):
    def test_initial_siren_unavailable_is_deferred_without_warning(self):
        gate = SirenStartupOffGate()
        self.assertTrue(gate.defer(initializing=True, available=False, now=100))
        self.assertTrue(gate.pending)
        self.assertFalse(gate.warning_due(100))
        self.assertFalse(gate.warning_due(100 + STARTUP_SIREN_GRACE_SECONDS - 1))
        self.assertTrue(gate.defer(initializing=False, available=False, now=101))
        self.assertFalse(gate.warning_due(101))

    def test_recovers_when_entity_and_service_appear(self):
        gate = SirenStartupOffGate()
        gate.defer(initializing=True, available=False, now=100)
        self.assertFalse(gate.defer(initializing=False, available=True, now=105))
        self.assertTrue(gate.pending)  # caller still owes an OFF
        gate.completed()  # only a successful service call clears the gate
        self.assertFalse(gate.pending)
        self.assertFalse(gate.defer(initializing=False, available=False, now=106))

    def test_long_unavailable_warns_once_and_keeps_retrying(self):
        gate = SirenStartupOffGate()
        gate.defer(initializing=True, available=False, now=0)
        self.assertFalse(gate.warning_due(119))
        self.assertTrue(gate.warning_due(120))
        self.assertFalse(gate.warning_due(121))
        self.assertTrue(gate.defer(initializing=False, available=False, now=150))
        self.assertTrue(gate.pending)

    def test_normal_disarm_after_startup_is_not_silenced(self):
        gate = SirenStartupOffGate()
        self.assertFalse(gate.defer(initializing=False, available=False, now=0))
        self.assertFalse(gate.pending)


if __name__ == "__main__":
    unittest.main()
