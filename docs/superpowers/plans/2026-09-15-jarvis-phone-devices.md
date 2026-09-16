# Jarvis Phone & Device Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable multi-phone device subsystem for real Android devices, with Phone Link as an adapter, shared hand/computer input, and guarded automation.

**Architecture:** Keep provider-neutral device contracts under `quality_of_life/devices/`. Map device operations into the existing capability catalog/policy. Add a Windows/Phone Link adapter interface without requiring Phone Link or a live phone in CI; fake providers provide deterministic integration tests.

**Tech Stack:** Python 3.11–3.13, dataclasses, typing Protocols, unittest, existing quality-of-life capability/permission/scheduler infrastructure.

**Spec:** `docs/superpowers/specs/2026-09-15-jarvis-phone-devices-design.md`

## Global Constraints
- No Android emulator dependency.
- Real-phone behavior is provider-capability-driven and must fail explicitly when unsupported.
- Phone mutations are deny-by-default through the existing capability policy and confirmation gates.
- CI must remain free of live-device dependencies.
- Existing computer/hand control remains the common input path.
- Production `main` is not modified by this implementation branch.

---

### Task 1: Device domain models

**Files:**
- Create: `quality_of_life/devices/__init__.py`
- Create: `quality_of_life/devices/models.py`
- Test: `tests/test_phone_devices_models.py`

**Interfaces:**
- `DeviceCapability` enum with `STATE_READ`, `SCREEN_VIEW`, `INPUT_CONTROL`, `NOTIFICATION_READ`, `CALLS`, `MESSAGES`, `FILES`, `APP_CONTROL`, `AUTOMATION`.
- `DeviceState` dataclass containing `device_id`, `label`, `connected`, `battery_percent`, `charging`, and optional `provider`.
- `DeviceResult` dataclass containing `ok`, `code`, `message`, optional `data`.

- [ ] Step 1: Write failing model construction/serialization tests.
- [ ] Step 2: Run `python -m unittest tests.test_phone_devices_models -v`; expected failures for missing models.
- [ ] Step 3: Implement the enums and immutable dataclasses with validation for IDs and battery bounds.
- [ ] Step 4: Re-run the focused tests; expected PASS.
- [ ] Step 5: Commit with `feat: add phone device domain models`.

### Task 2: Provider protocol and fake provider

**Files:**
- Create: `quality_of_life/devices/provider.py`
- Create: `quality_of_life/devices/fake_provider.py`
- Test: `tests/test_phone_device_provider.py`

**Interfaces:**
- `PhoneDeviceProvider` protocol: `list_devices()`, `get_state(device_id)`, `capabilities(device_id)`, `view_screen(device_id)`, `send_input(device_id, event)`, `read_notifications(device_id)`, `transfer_file(device_id, direction, path)`, `open_app(device_id, app_id)`, and `close()`.
- Methods return `DeviceResult` or typed state/capability values and never claim success after provider failure.
- `FakePhoneProvider` supports configurable devices/capabilities and records dispatched operations for assertions.

- [ ] Step 1: Write failing tests for provider contract, unsupported capability, disconnected-device failure, and operation recording.
- [ ] Step 2: Run focused provider tests; expected FAIL.
- [ ] Step 3: Implement the protocol and deterministic fake provider.
- [ ] Step 4: Run focused provider tests; expected PASS.
- [ ] Step 5: Commit with `feat: add phone device provider contract`.

### Task 3: Device registry and active-device context

**Files:**
- Create: `quality_of_life/devices/registry.py`
- Test: `tests/test_phone_device_registry.py`

**Interfaces:**
- `DeviceRegistry.register_provider(provider)`
- `DeviceRegistry.refresh()`
- `DeviceRegistry.list()`
- `DeviceRegistry.get(device_id)`
- `DeviceRegistry.select(device_id)`
- `DeviceRegistry.active()`
- `DeviceRegistry.remove(device_id)`

The registry must merge device identities deterministically, reject duplicate IDs from conflicting providers, and never silently select an unauthorized device.

- [ ] Step 1: Write failing tests for multi-device registration, selection, removal, duplicate IDs, and provider refresh errors.
- [ ] Step 2: Run the focused registry tests; expected FAIL.
- [ ] Step 3: Implement the registry and active-device state.
- [ ] Step 4: Run focused registry tests; expected PASS.
- [ ] Step 5: Commit with `feat: add multi-phone device registry`.

### Task 4: Permission/capability integration

**Files:**
- Modify: `quality_of_life/permissions.py`
- Modify: `quality_of_life/capabilities.py`
- Create: `tests/test_phone_device_permissions.py`

**Interfaces:**
- Add device capabilities to `Capability`.
- Add catalog operations such as `devices.list`, `devices.state`, `devices.screen`, `devices.input`, `devices.notifications`, `devices.files`, `devices.apps`, and `devices.automate`.
- `devices.screen` and read-only state are separate from mutating controls.

- [ ] Step 1: Write failing tests asserting every new operation maps to the expected capability/risk and disabled capabilities are denied.
- [ ] Step 2: Run focused permission tests; expected FAIL.
- [ ] Step 3: Add capability enums and catalog entries, preserving existing policy defaults.
- [ ] Step 4: Run focused tests plus `tests/test_qol_runtime.py`; expected PASS.
- [ ] Step 5: Commit with `feat: expose guarded phone device capabilities`.

### Task 5: Device control facade and automation hooks

**Files:**
- Create: `quality_of_life/devices/facade.py`
- Create: `quality_of_life/devices/automation.py`
- Test: `tests/test_phone_device_facade.py`
- Test: `tests/test_phone_device_automation.py`

**Interfaces:**
- `DeviceFacade.list_devices()`, `state(device_id)`, `select(device_id)`, `screen(device_id)`, `input(device_id, event)`, `notifications(device_id)`, `transfer(device_id, direction, path)`, `open_app(device_id, app_id)`.
- Each mutating method takes an explicit confirmation callback/policy decision before dispatch.
- `DeviceAutomation.run(action, device_id)` is cancellable and stops when state changes to disconnected.

- [ ] Step 1: Write failing facade tests for read operations, denied mutations, provider errors, and unsupported capability.
- [ ] Step 2: Write failing automation tests for targeted device execution, cancellation, disconnect stop, and repeated polling failure tolerance.
- [ ] Step 3: Run both focused test modules; expected FAIL.
- [ ] Step 4: Implement the facade and automation controller over the provider/registry/policy layers.
- [ ] Step 5: Run both focused modules; expected PASS.
- [ ] Step 6: Commit with `feat: add guarded phone device facade and automation`.

### Task 6: Hand-control and computer-control routing

**Files:**
- Modify: `quality_of_life/hand_control_runtime.py`
- Modify: `quality_of_life/computer_use.py`
- Create: `quality_of_life/devices/input_adapter.py`
- Test: `tests/test_phone_device_input.py`

**Interfaces:**
- `DeviceInputAdapter.route(event, target_device_id)` translates existing pointer/gesture events into provider input events without creating a second gesture vocabulary.
- Existing Windows computer control remains unchanged when no phone target is selected.

- [ ] Step 1: Write failing tests for phone-targeted click/move/scroll events and fallback to Windows control.
- [ ] Step 2: Run focused input tests; expected FAIL.
- [ ] Step 3: Implement the adapter and minimal routing hooks.
- [ ] Step 4: Run input tests plus existing hand-control integration tests; expected PASS.
- [ ] Step 5: Commit with `feat: route shared input to phone devices`.

### Task 7: Phone Link adapter boundary

**Files:**
- Create: `quality_of_life/devices/phone_link.py`
- Create: `tests/test_phone_link_adapter.py`
- Modify: `quality_of_life/devices/__init__.py`

**Interfaces:**
- `PhoneLinkProvider` implements `PhoneDeviceProvider` through a conservative Windows bridge surface.
- Discovery reports only capabilities that can be proven available; unavailable hooks return `UNAVAILABLE` without raising an infrastructure-level failure.
- The adapter must be import-safe on non-Windows and in CI without Phone Link installed.

- [ ] Step 1: Write failing adapter tests for non-Windows import, unavailable bridge behavior, capability mapping, and result normalization.
- [ ] Step 2: Run focused adapter tests; expected FAIL.
- [ ] Step 3: Implement the platform-gated adapter boundary without shelling out to arbitrary commands.
- [ ] Step 4: Run focused tests on the current platform; expected PASS.
- [ ] Step 5: Commit with `feat: add Windows Phone Link adapter boundary`.

### Task 8: Runtime wiring and documentation

**Files:**
- Modify: `quality_of_life/runtime.py`
- Modify: `quality_of_life/router.py`
- Modify: `quality_of_life/README.md`
- Create: `quality_of_life/README_DEVICES.md`
- Test: `tests/test_phone_device_integration.py`

**Interfaces:**
- Register the device facade in the existing runtime/tool catalog without making phone integration mandatory for startup.
- Add clear command/intents for listing devices, selecting one, viewing its screen, and running safe device automations.

- [ ] Step 1: Write failing integration tests for runtime discovery and intent dispatch with a fake provider.
- [ ] Step 2: Run the focused integration tests; expected FAIL.
- [ ] Step 3: Wire the device facade into the existing runtime and router while preserving all existing tool contracts.
- [ ] Step 4: Update device documentation with real-phone/Phone Link prerequisites and explicit feature limitations.
- [ ] Step 5: Run focused integration tests; expected PASS.
- [ ] Step 6: Commit with `feat: integrate phone device subsystem with Jarvis runtime`.

### Task 9: Full regression, packaging, and safety gates

**Files:**
- Modify: `.github/workflows/quality-of-life-tests.yml` only if required to explicitly include the new suite.

- [ ] Step 1: Run all phone-device tests together.
- [ ] Step 2: Run the complete unittest suite.
- [ ] Step 3: Run every existing CI workflow on the test branch.
- [ ] Step 4: Inspect every job and artifact, including compilation of every Python module and extracted portable bundle validation.
- [ ] Step 5: Fix only demonstrated failures and rerun the affected gate plus the full suite.
- [ ] Step 6: Commit any final test-only corrections.

### Task 10: Final test-copy review

- [ ] Step 1: Compare changed files against the test branch base and verify there are no unrelated changes.
- [ ] Step 2: Confirm no production `main` ref changed during implementation.
- [ ] Step 3: Confirm all declared acceptance criteria in the spec have test coverage or an explicit platform limitation.
- [ ] Step 4: Only after all gates are green, prepare a promotion PR from the test branch; do not merge it automatically.
