# Denon AVR integration for Remote Two/3 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

_Changes in the next release_

---

## v0.8.2 - 2025-05-27
### Fixed
- Temporary fix for HDMI output, ECO, dimmer and direct commands that don't work ([#69](https://github.com/unfoldedcircle/integration-denonavr/pull/69)).

## v0.8.1 - 2025-05-19
### Fixed
- Startup error after the first setup on a clean device ([#67](https://github.com/unfoldedcircle/integration-denonavr/issues/67)).

## v0.8.0 - 2025-05-13
### Added
- Multi-device support ([#20](https://github.com/unfoldedcircle/integration-denonavr/issues/20)).
- Additional commands. Contributed by @henrikwidlund, thanks! ([#65](https://github.com/unfoldedcircle/integration-denonavr/pull/65))

### Changed
- Update denonavr library to 1.1.0, remove hybrid connection.
- Use built-in API for setting timeouts. Contributed by @henrikwidlund, thanks! ([#66](https://github.com/unfoldedcircle/integration-denonavr/pull/66))

## v0.7.1 - 2025-04-26
### Changed
- update ucapi to 0.3.0

## v0.7.0 - 2025-04-25
### Fixed
- Missing response status codes when using http requests lead to timeout errors in UI. Contributed by @henrikwidlund, thanks! ([#58](https://github.com/unfoldedcircle/integration-denonavr/pull/58))
- Power toggle command ([#59](https://github.com/unfoldedcircle/integration-denonavr/pull/59)).

### Changed
- Add a support article link and change the setup description in the first setup flow screen.
- Use a nicer FontAwesome icon for the integration (tv-music).
- Update the embedded Python runtime to 3.11.12 and upgrade common Python libraries like zeroconf and websockets.

## v0.6.2 - 2025-04-07
### Fixed
- Adjust command timeout and settings menu. Contributed by @henrikwidlund, thanks! ([#56](https://github.com/unfoldedcircle/integration-denonavr/pull/56))

## v0.6.1 - 2025-03-24
### Changed
- Maintain ability to skip telnet in hybrid mode. Contributed by @henrikwidlund, thanks! ([#55](https://github.com/unfoldedcircle/integration-denonavr/pull/55))

## v0.6.0 - 2025-01-10
### Added
- Add option for hybrid telnet and http connection. Contributed by @henrikwidlund, thanks! ([#53](https://github.com/unfoldedcircle/integration-denonavr/pull/53))

## v0.5.1 - 2024-12-23
### Fixed
- Set the device state to connected after adding a new device in the setup flow.
### Changed
- Improved reconnection delay by not always calling setup. Contributed by @albaintor, thanks! ([#49])(https://github.com/unfoldedcircle/integration-denonavr/pull/49)
- Workaround for setup flow in web-configurator, not showing the first screen with address field.
- Updated denonavr, pyee and uc-api libraries.
- Replaced EOL GitHub action for release creation ([#52](https://github.com/unfoldedcircle/integration-denonavr/issues/52)).

## v0.5.0 - 2024-12-06
### Added
- New commands contributed by @henrikwidlund, thanks! ([#47](https://github.com/unfoldedcircle/integration-denonavr/pull/47), [#48](https://github.com/unfoldedcircle/integration-denonavr/pull/48))
  - Adjusting all channel levels
  - Adjusting delays
  - Discrete commands for setting surround modes and switching between next and previous
  - MultiEQ/Audyssey settings
  - Dirac Live controls
  - ECO modes
  - Status (Denon only)

## v0.4.2 - 2024-07-23
### Changed
- Create a one-folder bundle with PyInstaller instead a one-file bundle to save resources.
- Change archive format to the custom integration installation archive.
- Change default `driver_id` value in `driver.json` to create a compatible custom installation archive.

## v0.4.1 - 2024-06-19
### Fixed
- Invalid logging configuration in v0.4.0

## v0.4.0 - 2024-06-14
### Added
- Configurable volume step (in setup flow) and improved refresh of volume. Contributed by @albaintor, thanks! ([#38](https://github.com/unfoldedcircle/integration-denonavr/issues/38))
- New commands for Output Monitor 1, Monitor 2, Monitor Auto. Contributed by @splattner, thanks! ([#37](https://github.com/unfoldedcircle/integration-denonavr/issues/37))
- New commands: dim display, power toggle, trigger 1 & 2 ([#37](https://github.com/unfoldedcircle/integration-denonavr/issues/37)).
### Fixed
- Prevent disconnect state deadlock after setup or when aborting setup.

## v0.3.0 - 2024-03-18
### Added
- New commands: dpad, menu, context_menu and info. Contributed by @albaintor, thanks! ([#33](https://github.com/unfoldedcircle/integration-denonavr/issues/33)).

## v0.2.4 - 2024-02-17
### Fixed
- Remove reconnect delay after standby. Requires new Remote Two firmware ([unfoldedcircle/feature-and-bug-tracker#320](https://github.com/unfoldedcircle/feature-and-bug-tracker/issues/320)).

## v0.2.3 - 2023-11-18
### Added
- Manual setup mode

## v0.2.2 - 2023-11-15
### Fixed
- Set correct version in driver.json

## v0.2.1 - 2023-11-15
### Fixed
- Sound mode parameter name
- Telnet TA parameter check
- Discovery error handling during reconnect
- Reconnect race condition

## v0.2.0 - 2023-11-13
### Added
- Reconnect handling, poll mode instead of Telnet
### Fixed
- Device discovery
- Expected state handling
### Changed
- Use Python 3.11 and update dependencies
- Use integration library 0.1.1 from PyPI
- Code refactoring, enum classes, state handling
