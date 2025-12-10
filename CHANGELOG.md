# Denon AVR integration for Remote Two/3 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

_Changes in the next release_

### Fixed
- Remove max volume event caching for guaranteed event handling when running on the Remote device. Events are not always emitted at the same time or order.

---

## v0.12.2 - 2025-12-09
### Fixed
- Use default for maximum volume, since it is not always sent by the AVR.

## v0.12.1 - 2025-12-09
### Fixed
- Guard against decrease/increase volume outside valid volume range ([#149](https://github.com/unfoldedcircle/integration-denonavr/pull/149)).

## v0.12.0 - 2025-12-08
### Fixed
- Power off command in remote-entity throws an error.
- Slow volume changes and updates when using http by @henrikwidlund ([#42](https://github.com/unfoldedcircle/integration-denonavr/issues/42), [#135](https://github.com/unfoldedcircle/integration-denonavr/issues/135)).
- Add rate limiter to avoid commands from executing after releasing button by @henrikwidlund ([#145](https://github.com/unfoldedcircle/integration-denonavr/pull/145)).

## v0.11.5 - 2025-12-01
### Fixed
- Invalid send_cmd when using a remote-entity ([#126](https://github.com/unfoldedcircle/integration-denonavr/issues/126)).
- Invalid command map and validation ([#141](https://github.com/unfoldedcircle/integration-denonavr/pull/141)).

## v0.11.4 - 2025-11-25
### Fixed
- Telnet callbacks were no longer processed, stopping all dynamic state updates ([#140](https://github.com/unfoldedcircle/integration-denonavr/pull/140)).

## v0.11.3 - 2025-11-25
### Fixed
- Channel down command in media-player entity.

## v0.11.2 - 2025-11-24
### Fixed
- Not disconnecting the AVR(s) if a Remote client disconnects ([#137](https://github.com/unfoldedcircle/integration-denonavr/issues/137)).

### Added
- Initial unit tests.

## v0.11.1 - 2025-11-19
### Added
- Add discrete commands for stereo and mono by @henrikwidlund ([#132](https://github.com/unfoldedcircle/integration-denonavr/pull/132)).
- Support for more commands: Dolby Atmos Toggle, Page/Ch Up/Down, Input Mode (Select, Auto, HDMI, Digital, Analog) by @henrikwidlund ([#133](https://github.com/unfoldedcircle/integration-denonavr/pull/135).

### Changed
- Updated denonavr library ([#131](https://github.com/unfoldedcircle/integration-denonavr/pull/131)).
- Updated GitHub build action dependencies.

## v0.11.0 - 2025-10-02
### Fixed
- Eco off command text in remote-entity UI screen.
- Volume commands in http-mode.
- Incorrect initialization check for events ([#125](https://github.com/unfoldedcircle/integration-denonavr/pull/125)).
- Number parameter retrieval and validation from remote-entity command, limit repeat count to 20.

### Changed
- Add denonavr library as git submodule by @henrikwidlund ([#119](https://github.com/unfoldedcircle/integration-denonavr/pull/119)).
- Improve performance, new Marantz commands, fix Quick/smart select by @henrikwidlund ([#122](https://github.com/unfoldedcircle/integration-denonavr/pull/122)).

## v0.10.3 - 2025-09-17
### Changed
- Update embedded Python runtime to 3.11.13 and pyinstaller to 6.16.0.

## v0.10.2 - 2025-08-14
### Fixed
- Use manufacturer when checking if device is a Denon or Marantz receiver ([#108](https://github.com/unfoldedcircle/integration-denonavr/issues/108)).

### Changed
- Set timeout configuration step to 1 sec. Custom values can still be entered manually.

## v0.10.1 - 2025-08-04
### Fixed
- Incorrect remote-entity page names by @henrikwidlund ([#104](https://github.com/unfoldedcircle/integration-denonavr/pull/104)).

### Changed
- Update denonavr dependency and remove workarounds ([#105](https://github.com/unfoldedcircle/integration-denonavr/pull/105)).

## v0.10.0 - 2025-07-23
Again major additions by @henrikwidlund, thanks!
### Added
- Add remote entity to the integration with support for raw commands by @henrikwidlund ([#87](https://github.com/unfoldedcircle/integration-denonavr/issues/87)).
- Add discreet commands for inputs by @henrikwidlund ([#101](https://github.com/unfoldedcircle/integration-denonavr/pull/101), [feature-and-bug-tracker#527](https://github.com/unfoldedcircle/feature-and-bug-tracker/issues/527)).
- Add support for Quick/Smart commands by @henrikwidlund ([#98](https://github.com/unfoldedcircle/integration-denonavr/issues/98), [feature-and-bug-tracker#486](https://github.com/unfoldedcircle/feature-and-bug-tracker/issues/486)).

## v0.9.0 - 2025-07-04
Lots of contributions by @henrikwidlund, thanks!
### Fixed
- Fix power state mismatch by @henrikwidlund ([#89](https://github.com/unfoldedcircle/integration-denonavr/pull/89)).
- Fix update of volume when using HTTP by @henrikwidlund ([#90](https://github.com/unfoldedcircle/integration-denonavr/pull/90)).

### Added
- Add HEOS playback control support for Denon and discrete mute control by @henrikwidlund ([#91](https://github.com/unfoldedcircle/integration-denonavr/pull/91)).

### Changed
- Only subscribe to events we're interested in by @henrikwidlund ([#85](https://github.com/unfoldedcircle/integration-denonavr/pull/85)).
- Include Marantz in the driver name by @henrikwidlund ([#86](https://github.com/unfoldedcircle/integration-denonavr/pull/86)).
- Decrease the polling interval to keep state up to date by @henrikwidlund ([#88](https://github.com/unfoldedcircle/integration-denonavr/pull/88)).
- Update denonavr library to 1.1.1

## v0.8.4 - 2025-06-06
### Fixed
- Timeunits in connection and request timeouts ([#84](https://github.com/unfoldedcircle/integration-denonavr/pull/84)).

### Added
- Externalize language strings for translations with Crowdin ([#27](https://github.com/unfoldedcircle/integration-denonavr/issues/27)))
- Add Swedish translation. Contributed by @henrikwidlund, thanks!

## v0.8.3 - 2025-06-04
### Added
- Make connection and request timeouts configurable. Contributed by @henrikwidlund, thanks! ([#70](https://github.com/unfoldedcircle/integration-denonavr/pull/70)).

## v0.8.2 - 2025-05-27
### Fixed
- Temporary fix for HDMI output, ECO, dimmer and dirac commands that don't work ([#69](https://github.com/unfoldedcircle/integration-denonavr/pull/69)).

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
