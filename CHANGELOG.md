# Denon AVR integration for Remote Two/3 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

_Changes in the next release_

---

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
