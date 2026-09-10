# Cursor_Ankit

## Traffic Light FSM

This repository contains a finite state machine implementation for a traffic light controller.

### States

- `STARTUP`
- `RED`
- `GREEN`
- `YELLOW`
- `FAULT`

### Events

- `POWER_ON`
- `TIMER_EXPIRED`
- `RESET`
- `FAULT_DETECTED`
- `FAULT_CLEARED`

### State flow

`STARTUP -> RED -> GREEN -> YELLOW -> RED`

Any state can transition to `FAULT`, and `FAULT` returns to `RED` only after `FAULT_CLEARED` followed by `RESET`.

### Features

- Configurable red, green, yellow, and fault flash timings
- Safe light outputs with one active light pattern per state
- Flashing red fault mode
- Invalid events leave the controller in its current safe state

### Run tests

```bash
python -m unittest
```
