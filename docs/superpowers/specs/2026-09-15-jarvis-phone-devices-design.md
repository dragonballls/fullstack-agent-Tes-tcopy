# Jarvis Phone & Device Control Design

**Goal:** Add an isolated device subsystem that models real Android phones as external devices, supports multiple phones, integrates with Windows/Phone Link where available, and exposes safe observation, control, and automation interfaces without introducing an Android emulator dependency.

## Scope
- Device registry with stable device IDs, labels, connection state, and capability discovery.
- Provider adapter boundary so Phone Link/Windows integration is one implementation rather than the core API.
- Capability-aware live-screen/control hooks for the actual phone; unsupported features return explicit unavailable results.
- Phone state, notifications, file-transfer, app-control, input-control, and automation abstractions.
- Reuse existing Jarvis permission and automation systems; phone actions remain deny-by-default and sensitive actions require confirmation unless policy explicitly allows them.
- Reuse existing hand-control/computer-control input events rather than creating a second gesture system.
- No LDPlayer dependency; no Android emulation.
- Multi-device selection and active-device context.
- Deterministic tests using fake providers; no live phone dependency in CI.

## Non-goals
- Implementing a new Android emulator.
- Bypassing Android/Windows security prompts or consent mechanisms.
- Claiming functionality that the connected phone/provider does not expose.
- Remote internet access in the first implementation; the provider API leaves room for a future secure remote transport.

## Architecture
`quality_of_life/devices/` owns device models, provider protocols, registry, policy mapping, and automation-facing operations. Existing `quality_of_life/capabilities.py`, `permissions.py`, `scheduler.py`, and hand/computer-control modules remain the policy and input foundations. A Windows Phone Link adapter can be implemented behind the provider protocol without making Phone Link mandatory for unit tests or other future Android transports.

## Safety and correctness
- Every mutating phone operation maps to a declared capability and operation risk.
- Operations return explicit status/results and never report success when a provider declines or is unavailable.
- Device IDs are opaque and provider-generated labels are not trusted as unique IDs.
- File paths and app identifiers are provider-scoped and validated before dispatch.
- Automation must be cancellable and must stop on provider disconnects.
- CI uses fake providers to cover success, unsupported capability, disconnected device, denied permission, cancellation, and provider error paths.

## Acceptance criteria
1. Multiple devices can be registered, listed, selected, and removed deterministically.
2. A fake provider can expose a live-screen/control surface and state; the registry reports capabilities accurately.
3. Phone operations pass through the existing capability/confirmation policy.
4. Automation can target a named device, survives ordinary provider polling failures, and cancels on disconnect.
5. Existing hand-control events can target a device through the common input path.
6. Existing full test suites remain green, with new phone tests included in the standard quality/release gates.
7. No production branch is changed until the test-copy implementation and all release gates are green.
