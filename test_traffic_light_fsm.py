import unittest

from traffic_light_fsm import Event, State, TimingConfig, TrafficLightFSM


class TrafficLightFSMTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fsm = TrafficLightFSM(
            TimingConfig(
                red_duration=5.0,
                green_duration=4.0,
                yellow_duration=2.0,
                fault_flash_interval=1.0,
            )
        )

    def test_starts_in_startup_with_all_lights_off(self) -> None:
        self.assertEqual(self.fsm.state, State.STARTUP)
        self.assertFalse(self.fsm.output.red)
        self.assertFalse(self.fsm.output.yellow)
        self.assertFalse(self.fsm.output.green)

    def test_power_on_moves_to_red(self) -> None:
        self.fsm.handle_event(Event.POWER_ON)

        self.assertEqual(self.fsm.state, State.RED)
        self.assertTrue(self.fsm.output.red)
        self.assertFalse(self.fsm.output.yellow)
        self.assertFalse(self.fsm.output.green)

    def test_normal_cycle_follows_red_green_yellow_red(self) -> None:
        self.fsm.handle_event(Event.POWER_ON)
        self.fsm.advance(5.0)
        self.assertEqual(self.fsm.state, State.GREEN)

        self.fsm.advance(4.0)
        self.assertEqual(self.fsm.state, State.YELLOW)

        self.fsm.advance(2.0)
        self.assertEqual(self.fsm.state, State.RED)

    def test_large_advance_can_cross_multiple_states(self) -> None:
        self.fsm.handle_event(Event.POWER_ON)
        self.fsm.advance(10.0)

        self.assertEqual(self.fsm.state, State.YELLOW)

    def test_fault_detected_moves_to_fault_from_any_state(self) -> None:
        self.fsm.handle_event(Event.FAULT_DETECTED)

        self.assertEqual(self.fsm.state, State.FAULT)
        self.assertTrue(self.fsm.output.red)
        self.assertFalse(self.fsm.output.yellow)
        self.assertFalse(self.fsm.output.green)

    def test_fault_state_flashes_red(self) -> None:
        self.fsm.handle_event(Event.POWER_ON)
        self.fsm.handle_event(Event.FAULT_DETECTED)

        self.assertTrue(self.fsm.output.red)
        self.fsm.advance(1.0)
        self.assertFalse(self.fsm.output.red)
        self.fsm.advance(1.0)
        self.assertTrue(self.fsm.output.red)

    def test_fault_must_be_cleared_before_reset_returns_to_red(self) -> None:
        self.fsm.handle_event(Event.POWER_ON)
        self.fsm.handle_event(Event.FAULT_DETECTED)
        self.fsm.handle_event(Event.RESET)
        self.assertEqual(self.fsm.state, State.FAULT)

        self.fsm.handle_event(Event.FAULT_CLEARED)
        self.fsm.handle_event(Event.RESET)

        self.assertEqual(self.fsm.state, State.RED)
        self.assertTrue(self.fsm.output.red)

    def test_invalid_events_keep_current_safe_state(self) -> None:
        self.fsm.handle_event(Event.POWER_ON)
        self.fsm.handle_event(Event.RESET)

        self.assertEqual(self.fsm.state, State.RED)
        self.assertTrue(self.fsm.output.red)


if __name__ == "__main__":
    unittest.main()
