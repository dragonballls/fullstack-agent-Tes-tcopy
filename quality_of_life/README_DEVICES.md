# Jarvis Physical Device Control

Jarvis treats phones as real external devices, not Android emulators.

## Direct Android path

The `AndroidAdbProvider` discovers authorized physical Android devices through `adb devices`. Each device serial is a stable device ID for the current connection, so multiple phones can be managed independently.

When `scrcpy` is available, `devices.screen` starts a live interactive view for the selected physical device. The phone continues running its own Android system and applications.

Direct controls currently covered by the provider are taps, horizontal swipes, text entry, back/home/recent navigation, application launch, and file push/pull. Battery and charging state are read through `dumpsys battery`.

## Phone Link path

`PhoneLinkProvider` is deliberately a provider boundary. A Windows bridge can expose capabilities that Microsoft Phone Link makes available on a particular Windows/Android combination. The provider never assumes unsupported capabilities.

## Multiple phones

Register more than one provider device and select the active device by its opaque device ID or user label. The registry prevents a device ID from silently being claimed by two different providers.

## Automation

Device automations are routed through `DeviceAutomation`. They require the physical-device automation capability, accept a cancellation token, and return an explicit failure if the device disconnects during execution.

## Permissions

Device read, screen, input, notification, file, app, and automation operations are separate capabilities. Input, file, app, and automation mutations remain confirmation-gated by default.

## CI

No real phone, USB device, developer workstation, adb installation, or scrcpy installation is required for CI. Provider behavior is covered through deterministic fakes and injected command runners.
