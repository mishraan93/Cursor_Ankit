from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class State(Enum):
    STARTUP = auto()
    RED = auto()
    GREEN = auto()
    YELLOW = auto()
    FAULT = auto()


class Event(Enum):
    POWER_ON = auto()
    TIMER_EXPIRED = auto()
    RESET = auto()
    FAULT_DETECTED = auto()
    FAULT_CLEARED = auto()


@dataclass(frozen=True)
class TimingConfig:
    red_duration: float = 10.0
    green_duration: float = 10.0
    yellow_duration: float = 3.0
    fault_flash_interval: float = 1.0

    def __post_init__(self) -> None:
        for name, value in (
            ("red_duration", self.red_duration),
            ("green_duration", self.green_duration),
            ("yellow_duration", self.yellow_duration),
            ("fault_flash_interval", self.fault_flash_interval),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be greater than 0")


@dataclass(frozen=True)
class LightOutput:
    red: bool = False
    yellow: bool = False
    green: bool = False


class TrafficLightFSM:
    def __init__(self, timing: TimingConfig | None = None) -> None:
        self.timing = timing or TimingConfig()
        self.state = State.STARTUP
        self._elapsed = 0.0
        self._fault_cleared = False
        self._fault_red_on = True

    def handle_event(self, event: Event) -> State:
        if event == Event.FAULT_DETECTED:
            self._enter_fault()
            return self.state

        if self.state == State.STARTUP:
            if event == Event.POWER_ON:
                self._transition(State.RED)
            return self.state

        if self.state == State.RED:
            if event == Event.TIMER_EXPIRED:
                self._transition(State.GREEN)
            return self.state

        if self.state == State.GREEN:
            if event == Event.TIMER_EXPIRED:
                self._transition(State.YELLOW)
            return self.state

        if self.state == State.YELLOW:
            if event == Event.TIMER_EXPIRED:
                self._transition(State.RED)
            return self.state

        if self.state == State.FAULT:
            if event == Event.FAULT_CLEARED:
                self._fault_cleared = True
            elif event == Event.RESET and self._fault_cleared:
                self._transition(State.RED)
            return self.state

        return self.state

    def advance(self, seconds: float) -> State:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")

        self._elapsed += seconds

        if self.state == State.FAULT:
            self._advance_fault_flash()
            return self.state

        while self.state in {State.RED, State.GREEN, State.YELLOW}:
            duration = self._duration_for(self.state)
            if self._elapsed < duration:
                break
            self._elapsed -= duration
            self.handle_event(Event.TIMER_EXPIRED)

        return self.state

    @property
    def output(self) -> LightOutput:
        if self.state == State.RED:
            return LightOutput(red=True)
        if self.state == State.GREEN:
            return LightOutput(green=True)
        if self.state == State.YELLOW:
            return LightOutput(yellow=True)
        if self.state == State.FAULT:
            return LightOutput(red=self._fault_red_on)
        return LightOutput()

    def _enter_fault(self) -> None:
        self.state = State.FAULT
        self._elapsed = 0.0
        self._fault_cleared = False
        self._fault_red_on = True

    def _transition(self, next_state: State) -> None:
        self.state = next_state
        self._elapsed = 0.0
        if next_state != State.FAULT:
            self._fault_cleared = False
            self._fault_red_on = True

    def _duration_for(self, state: State) -> float:
        if state == State.RED:
            return self.timing.red_duration
        if state == State.GREEN:
            return self.timing.green_duration
        if state == State.YELLOW:
            return self.timing.yellow_duration
        raise ValueError(f"State {state.name} does not use timers")

    def _advance_fault_flash(self) -> None:
        interval = self.timing.fault_flash_interval
        while self._elapsed >= interval:
            self._elapsed -= interval
            self._fault_red_on = not self._fault_red_on
