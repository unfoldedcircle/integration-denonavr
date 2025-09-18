# Denon AVR integration for Remote Two/3

Using [denonavr](https://github.com/henrikwidlund/denonavr) (included as a git submodule)
and [uc-integration-api](https://github.com/aitatoi/integration-python-library),
[Crowdin translations](https://crowdin.com/project/uc-integration-denon-avr).

This integration is included in the Remote Two and Remote 3 firmware, and no external service must be run to connect
with Denon AVR devices.

‼️ Do not install this integration as a custom integration on the Remote, or it can interfere with the included version.  
Included integrations cannot be updated manually. The integration can be run as an external integration for testing and 
development.

- The driver discovers Denon or Marantz AVRs on the local network. Manual configuration by hostname or IP is also supported.  
- Multiple AVR devices are supported with version 0.8.0 and newer.
- A [media player entity](https://github.com/unfoldedcircle/core-api/blob/main/doc/entities/entity_media_player.md)
is exposed to the Remote to control the AVR.

Receivers can be controlled by HTTP or Telnet. Using Telnet provides realtime updates for many values, but certain
receivers are limited to a single connection only (see limitations below).

## Requirements

- To be able to power on the receiver from standby, the AVR *Network Control* setting must be set to: *Always On*
    - This setting can be found under: *Web Control, Network, Network Control*
- The following TCP ports need to be accessible if the AVR is behind a routed network or in a VLAN: 23, 8080, and 60006
- When using DHCP: a static IP address reservation for the AVR is recommended.
    - A fixed IP address can speed up reconnection after the Remote wakes up from standby.
    - This is required when using manual setup with an IP address. Otherwise, the AVR won’t be reachable anymore if it
      gets a new IP address assigned.

## Limitations and known issues

- Device discovery is using
  the [Simple Device Discovery Protocol](https://en.wikipedia.org/wiki/Simple_Service_Discovery_Protocol)
  (SSDP) to find a network receiver.
    - Unfortunately, this doesn’t work anymore for all models. If your receiver cannot be found when it is turned on, a
      manual setup with the IP address or hostname of the receiver is required. In this case, please either configure a
      static IP address in your receiver or use a DHCP IP reservation in your router / DHCP server.
- Telnet might be limited to one client connection only, depending on AVR model.
    - Older models only support a single connection. That means, if you have multiple Remotes that only one is able to
      use Telnet. If the AVR is already controlled by another system, for example your smart home controller, then the
      Remote can’t use Telnet anymore.
    - We have successfully tested multiple Telnet connections on newer AVR-X models.  
      Unfortunately, there’s no official documentation, which models support multiple connections. One has to try out if
      it works or not.
- A cold start of the AVR can take up to a minute or longer until it is reachable on the network and can be controlled
  by this integration.  
  Please keep this in mind when using a smart power switch to completely power off the AVR. For example, when using an
  activity to control the smart power switch, it requires a longer delay to send the AVR power-on command.
- HEOS control is not supported.

## Supported commands

Supported attributes in the media player entity:

- State (on, off, playing, paused, unknown)
- Volume, muted
- Input source
- Sound mode
- Title, Album, Artist, Artwork: only supported on some models.

Supported media player commands:

- Turn on & off, power toggle
- Volume up, down, mute
- Play/pause, next, previous
- Source select
- Sound mode select
- DPAD navigation, menu, context menu, info

Additional commands are exposed as "simple commands" that can be used in macros and activities. Many of these commands
are only supported by specific receiver models. Please check your manual what commands your receiver supports.
Note that the toggle commands only are available when using Telnet.

| Simple Command                                      | Denon Command         |
|-----------------------------------------------------|-----------------------|
| OUTPUT_1                                            | VSMONI1               |
| OUTPUT_2                                            | VSMONI2               |
| OUTPUT_AUTO                                         | VSMONIAUTO            |
| DIMMER_TOGGLE                                       | DIM SEL               |
| DIMMER_BRIGHT                                       | DIM BRI               |
| DIMMER_DIM                                          | DIM DIM               |
| DIMMER_DARK                                         | DIM DAR               |
| DIMMER_OFF                                          | DIM OFF               |
| TRIGGER1_ON                                         | TR1 ON                |
| TRIGGER1_OFF                                        | TR1 OFF               |
| TRIGGER2_ON                                         | TR2 ON                |
| TRIGGER2_OFF                                        | TR2 OFF               |
| TRIGGER3_ON                                         | TR2 ON                |
| TRIGGER3_OFF                                        | TR2 OFF               |
| DELAY_UP                                            | PSDELAY UP            |
| DELAY_DOWN                                          | PSDELAY DOWN          |
| ECO_AUTO                                            | ECOAUTO               |
| ECO_ON                                              | ECOON                 |
| ECO_OFF                                             | ECOOFF                |
| INFO_MENU                                           | MNINF                 |
| CHANNEL_LEVEL_ADJUST_MENU                           | MNCHL                 |
| AUTO_STANDBY_OFF                                    | STBYOFF               |
| AUTO_STANDBY_15MIN                                  | STBY15M               |
| AUTO_STANDBY_30MIN                                  | STBY30M               |
| AUTO_STANDBY_60MIN                                  | STBY60M               |
| DELAY_TIME_UP                                       | PSDEL UP              |
| DELAY_TIME_DOWN                                     | PSDEL DOWN            |
| HDMI_AUDIO_DECODE_AMP                               | VSAUDIO AMP           |
| HDMI_AUDIO_DECODE_TV                                | VSAUDIO TV            |
| VIDEO_PROCESSING_MODE_AUTO                          | VSVPMAUTO             |
| VIDEO_PROCESSING_MODE_GAME                          | VSVPMGAME             |
| VIDEO_PROCESSING_MODE_MOVIE                         | VSVPMOVI              |
| VIDEO_PROCESSING_MODE_BYPASS                        | VSVPMBYP              |
| NETWORK_RESTART                                     | NSRBT                 |
| SPEAKER_PRESET_1                                    | SPPR 1                |
| SPEAKER_PRESET_2                                    | SPPR 2                |
| SPEAKER_PRESET_TOGGLE                               | SPPR 1/2              |
| BT_TRANSMITTER_ON                                   | BTTX ON               |
| BT_TRANSMITTER_OFF                                  | BTTX OFF              |
| BT_TRANSMITTER_TOGGLE                               | BTTX ON/OFF           |
| BT_OUTPUT_MODE_BT_SPEAKER                           | BTTX SP               |
| BT_OUTPUT_MODE_BT_ONLY                              | BTTX BT               |
| BT_OUTPUT_MODE_TOGGLE                               | BTTX SP/BT            |
| AUDIO_RESTORER_OFF                                  | PSRSTR OFF            |
| AUDIO_RESTORER_LOW                                  | PSRSTR LOW            |
| AUDIO_RESTORER_MEDIUM                               | PSRSTR MED            |
| AUDIO_RESTORER_HIGH                                 | PSRSTR HI             |
| REMOTE_CONTROL_LOCK_ON                              | SYREMOTE LOCK ON      |
| REMOTE_CONTROL_LOCK_OFF                             | SYREMOTE LOCK OFF     |
| PANEL_LOCK_PANEL                                    | SYPANEL LOCK ON       |
| PANEL_LOCK_PANEL_VOLUME                             | SYPANEL+V LOCK ON     |
| PANEL_LOCK_OFF                                      | SYPANEL LOCK OFF      |
| GRAPHIC_EQ_ON                                       | PSGEQ ON              |
| GRAPHIC_EQ_OFF                                      | PSGEQ OFF             |
| GRAPHIC_EQ_TOGGLE                                   | PSGEQ ON/OFF          |
| HEADPHONE_EQ_ON                                     | PSHEQ ON              |
| HEADPHONE_EQ_OFF                                    | PSHEQ OFF             |
| HEADPHONE_EQ_TOGGLE                                 | PSHEQ ON/OFF          |
| STATUS                                              | RCSHP0230030          |
| FRONT_LEFT_UP                                       | CVFL UP               |
| FRONT_LEFT_DOWN                                     | CVFL DOWN             |
| FRONT_RIGHT_UP                                      | CVFR UP               |
| FRONT_RIGHT_DOWN                                    | CVFR DOWN             |
| CENTER_UP                                           | CVC UP                |
| CENTER_DOWN                                         | CVC DOWN              |
| SUB1_UP                                             | CVSW UP               |
| SUB1_DOWN                                           | CVSW DOWN             |
| SUB2_UP                                             | CVSW2 UP              |
| SUB2_DOWN                                           | CVSW2 DOWN            |
| SUB3_UP                                             | CVSW3 UP              |
| SUB3_DOWN                                           | CVSW3 DOWN            |
| SUB4_UP                                             | CVSW4 UP              |
| SUB4_DOWN                                           | CVSW4 DOWN            |
| SURROUND_LEFT_UP                                    | CVSL UP               |
| SURROUND_LEFT_DOWN                                  | CVSL DOWN             |
| SURROUND_RIGHT_UP                                   | CVSR UP               |
| SURROUND_RIGHT_DOWN                                 | CVSR DOWN             |
| SURROUND_BACK_LEFT_UP                               | CVSBL UP              |
| SURROUND_BACK_LEFT_DOWN                             | CVSBL DOWN            |
| SURROUND_BACK_RIGHT_UP                              | CVSBR UP              |
| SURROUND_BACK_RIGHT_DOWN                            | CVSBR DOWN            |
| FRONT_HEIGHT_LEFT_UP                                | CVFHL UP              |
| FRONT_HEIGHT_LEFT_DOWN                              | CVFHL DOWN            |
| FRONT_HEIGHT_RIGHT_UP                               | CVFHR UP              |
| FRONT_HEIGHT_RIGHT_DOWN                             | CVFHR DOWN            |
| FRONT_WIDE_LEFT_UP                                  | CVFWL UP              |
| FRONT_WIDE_LEFT_DOWN                                | CVFWL DOWN            |
| FRONT_WIDE_RIGHT_UP                                 | CVFWR UP              |
| FRONT_WIDE_RIGHT_DOWN                               | CVFWR DOWN            |
| TOP_FRONT_LEFT_UP                                   | CVTFL UP              |
| TOP_FRONT_LEFT_DOWN                                 | CVTFL DOWN            |
| TOP_FRONT_RIGHT_UP                                  | CVTFR UP              |
| TOP_FRONT_RIGHT_DOWN                                | CVTFR DOWN            |
| TOP_MIDDLE_LEFT_UP                                  | CVTML UP              |
| TOP_MIDDLE_LEFT_DOWN                                | CVTML DOWN            |
| TOP_MIDDLE_RIGHT_UP                                 | CVTMR UP              |
| TOP_MIDDLE_RIGHT_DOWN                               | CVTMR DOWN            |
| TOP_REAR_LEFT_UP                                    | CVTRL UP              |
| TOP_REAR_LEFT_DOWN                                  | CVTRL DOWN            |
| TOP_REAR_RIGHT_UP                                   | CVTRR UP              |
| TOP_REAR_RIGHT_DOWN                                 | CVTRR DOWN            |
| REAR_HEIGHT_LEFT_UP                                 | CVRHL UP              |
| REAR_HEIGHT_LEFT_DOWN                               | CVRHL DOWN            |
| REAR_HEIGHT_RIGHT_UP                                | CVRHR UP              |
| REAR_HEIGHT_RIGHT_DOWN                              | CVRHR DOWN            |
| FRONT_DOLBY_LEFT_UP                                 | CVFDL UP              |
| FRONT_DOLBY_LEFT_DOWN                               | CVFDL DOWN            |
| FRONT_DOLBY_RIGHT_UP                                | CVFDR UP              |
| FRONT_DOLBY_RIGHT_DOWN                              | CVFDR DOWN            |
| SURROUND_DOLBY_LEFT_UP                              | CVSDL UP              |
| SURROUND_DOLBY_LEFT_DOWN                            | CVSDL DOWN            |
| SURROUND_DOLBY_RIGHT_UP                             | CVSDR UP              |
| SURROUND_DOLBY_RIGHT_DOWN                           | CVSDR DOWN            |
| BACK_DOLBY_LEFT_UP                                  | CVBDL UP              |
| BACK_DOLBY_LEFT_DOWN                                | CVBDL DOWN            |
| BACK_DOLBY_RIGHT_UP                                 | CVBDR UP              |
| BACK_DOLBY_RIGHT_DOWN                               | CVBDR DOWN            |
| SURROUND_HEIGHT_LEFT_UP                             | CVSHL UP              |
| SURROUND_HEIGHT_LEFT_DOWN                           | CVSHL DOWN            |
| SURROUND_HEIGHT_RIGHT_UP                            | CVSHR UP              |
| SURROUND_HEIGHT_RIGHT_DOWN                          | CVSHR DOWN            |
| TOP_SURROUND_UP                                     | CVTS UP               |
| TOP_SURROUND_DOWN                                   | CVTS DOWN             |
| CENTER_HEIGHT_UP                                    | CVCH UP               |
| CENTER_HEIGHT_DOWN                                  | CVCH DOWN             |
| CHANNEL_VOLUMES_RESET                               | CVZRL                 |
| SUBWOOFER_ON                                        | PSSWR ON              |
| SUBWOOFER_OFF                                       | PSSWR OFF             |
| SUBWOOFER_TOGGLE                                    | PSSWR ON/OFF          |
| SUBWOOFER1_LEVEL_UP                                 | PSSWL UP              |
| SUBWOOFER1_LEVEL_DOWN                               | PSSWL DOWN            |
| SUBWOOFER2_LEVEL_UP                                 | PSSWL2 UP             |
| SUBWOOFER2_LEVEL_DOWN                               | PSSWL2 DOWN           |
| SUBWOOFER3_LEVEL_UP                                 | PSSWL3 UP             |
| SUBWOOFER3_LEVEL_DOWN                               | PSSWL3 DOWN           |
| SUBWOOFER4_LEVEL_UP                                 | PSSWL4 UP             |
| SUBWOOFER4_LEVEL_DOWN                               | PSSWL4 DOWN           |
| LFE_UP                                              | PSLFE UP              |
| LFE_DOWN                                            | PSLFE DOWN            |
| BASS_SYNC_UP                                        | PSBSC UP              |
| BASS_SYNC_DOWN                                      | PSBSC DOWN            |
| SURROUND_MODE_AUTO                                  | MSAUTO                |
| SURROUND_MODE_DIRECT                                | MSDIRECT              |
| SURROUND_MODE_PURE_DIRECT                           | MSPURE DIRECT         |
| SURROUND_MODE_DOLBY_DIGITAL                         | MSDOLBY DIGITAL       |
| SURROUND_MODE_DTS_SURROUND                          | MSDTS SURROUND        |
| SURROUND_MODE_AURO3D                                | MSAURO3D              |
| SURROUND_MODE_AURO2DSURR                            | MSAURO2DSURR          |
| SURROUND_MODE_MCH_STEREO                            | MSMCH STEREO          |
| SURROUND_MODE_NEXT                                  | MSRIGHT               |
| SURROUND_MODE_PREVIOUS                              | MSLEFT                |
| SOUND_MODE_NEURAL_X_ON                              | PSNEURAL ON           |
| SOUND_MODE_NEURAL_X_OFF                             | PSNEURAL OFF          |
| SOUND_MODE_NEURAL_X_TOGGLE                          | PSNEURAL ON/OFF       |
| SOUND_MODE_IMAX_AUTO                                | PSIMAX AUTO           |
| SOUND_MODE_IMAX_OFF                                 | PSIMAX OFF            |
| SOUND_MODE_IMAX_TOGGLE                              | PSIMAX AUTO/OFF       |
| IMAX_AUDIO_SETTINGS_AUTO                            | PSIMAXAUD AUTO        |
| IMAX_AUDIO_SETTINGS_MANUAL                          | PSIMAXAUD MANUAL      |
| IMAX_AUDIO_SETTINGS_TOGGLE                          | PSIMAXAUD AUTO/MANUAL |
| IMAX_HPF_40HZ                                       | PSIMAXHPF 40          |
| IMAX_HPF_60HZ                                       | PSIMAXHPF 60          |
| IMAX_HPF_80HZ                                       | PSIMAXHPF 80          |
| IMAX_HPF_90HZ                                       | PSIMAXHPF 90          |
| IMAX_HPF_100HZ                                      | PSIMAXHPF 100         |
| IMAX_HPF_110HZ                                      | PSIMAXHPF 110         |
| IMAX_HPF_120HZ                                      | PSIMAXHPF 120         |
| IMAX_HPF_150HZ                                      | PSIMAXHPF 150         |
| IMAX_HPF_180HZ                                      | PSIMAXHPF 180         |
| IMAX_HPF_200HZ                                      | PSIMAXHPF 200         |
| IMAX_HPF_250HZ                                      | PSIMAXHPF 250         |
| IMAX_LPF_80HZ                                       | PSIMAXLPF 80          |
| IMAX_LPF_90HZ                                       | PSIMAXLPF 90          |
| IMAX_LPF_100HZ                                      | PSIMAXLPF 100         |
| IMAX_LPF_110HZ                                      | PSIMAXLPF 110         |
| IMAX_LPF_120HZ                                      | PSIMAXLPF 120         |
| IMAX_LPF_150HZ                                      | PSIMAXLPF 150         |
| IMAX_LPF_180HZ                                      | PSIMAXLPF 180         |
| IMAX_LPF_200HZ                                      | PSIMAXLPF 200         |
| IMAX_LPF_250HZ                                      | PSIMAXLPF 250         |
| IMAX_SUBWOOFER_ON                                   | PSIMAXSWM ON          |
| IMAX_SUBWOOFER_OFF                                  | PSIMAXSWM OFF         |
| IMAX_SUBWOOFER_OUTPUT_LFE_MAIN                      | PSIMAXSWO L+M         |
| IMAX_SUBWOOFER_OUTPUT_LFE                           | PSIMAXSWO LFE         |
| CINEMA_EQ_ON                                        | PSCINEMA EQ.ON        |
| CINEMA_EQ_OFF                                       | PSCINEMA EQ.OFF       |
| CINEMA_EQ_TOGGLE                                    | PSCINEMA EQ.ON/OFF    |
| CENTER_SPREAD_ON                                    | PSCES ON              |
| CENTER_SPREAD_OFF                                   | PSCES OFF             |
| CENTER_SPREAD_TOGGLE                                | PSCES ON/OFF          |
| LOUDNESS_MANAGEMENT_ON                              | PSLOM ON              |
| LOUDNESS_MANAGEMENT_OFF                             | PSLOM OFF             |
| LOUDNESS_MANAGEMENT_TOGGLE                          | PSLOM ON/OFF          |
| DIALOG_ENHANCER_OFF                                 | PSDEH OFF             |
| DIALOG_ENHANCER_LOW                                 | PSDEH LOW             |
| DIALOG_ENHANCER_MEDIUM                              | PSDEH MED             |
| DIALOG_ENHANCER_HIGH                                | PSDEH HIGH            |
| AUROMATIC_3D_PRESET_SMALL                           | PSAUROPR SMA          |
| AUROMATIC_3D_PRESET_MEDIUM                          | PSAUROPR MED          |
| AUROMATIC_3D_PRESET_LARGE                           | PSAUROPR LAR          |
| AUROMATIC_3D_PRESET_SPEECH                          | PSAUROPR SPE          |
| AUROMATIC_3D_PRESET_MOVIE                           | PSAUROPR MOV          |
| AUROMATIC_3D_STRENGTH_UP                            | PSAUROST UP           |
| AUROMATIC_3D_STRENGTH_DOWN                          | PSAUROST DOWN         |
| AURO_3D_MODE_DIRECT                                 | PSAUROMODE DRCT       |
| AURO_3D_MODE_CHANNEL_EXPANSION                      | PSAUROMODE EXP        |
| DIALOG_CONTROL_UP                                   | PSDIC UP              |
| DIALOG_CONTROL_DOWN                                 | PSDIC DOWN            |
| SPEAKER_VIRTUALIZER_ON                              | PSSPV ON              |
| SPEAKER_VIRTUALIZER_OFF                             | PSSPV OFF             |
| SPEAKER_VIRTUALIZER_TOGGLE                          | PSSPV ON/OFF          |
| EFFECT_SPEAKER_SELECTION_FLOOR                      | PSSP:FL               |
| EFFECT_SPEAKER_SELECTION_FRONT                      | PSSP:FR               |
| EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT               | PSSP:FH               |
| EFFECT_SPEAKER_SELECTION_FRONT_WIDE                 | PSSP:FW               |
| EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT_WIDE          | PSSP:HW               |
| EFFECT_SPEAKER_SELECTION_HEIGHT_FLOOR               | PSSP:HF               |
| EFFECT_SPEAKER_SELECTION_SURROUND_BACK              | PSSP:SB               |
| EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_HEIGHT | PSSP:BH               |
| EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_WIDE   | PSSP:BW               |
| DRC_AUTO                                            | PSDRC AUTO            |
| DRC_LOW                                             | PSDRC LOW             |
| DRC_MID                                             | PSDRC MID             |
| DRC_HI                                              | PSDRC HI              |
| DRC_OFF                                             | PSDRC OFF             |
| MULTIEQ_REFERENCE                                   | PSMULTEQ:AUDYSSEY     |
| MULTIEQ_BYPASS_LR                                   | MULTEQ:BYP.LR         |
| MULTIEQ_FLAT                                        | PSMULTEQ:FLAT         |
| MULTIEQ_OFF                                         | PSMULTEQ:OFF          |
| DYNAMIC_EQ_ON                                       | PSDYNEQ ON            |
| DYNAMIC_EQ_OFF                                      | PSDYNEQ OFF           |
| DYNAMIC_EQ_TOGGLE                                   | PSDYNEQ OFF           |
| DYNAMIC_VOLUME_OFF                                  | PSDYNVOL OFF          |
| AUDYSSEY_LFC                                        | PSLFC ON              |
| AUDYSSEY_LFC_OFF                                    | PSLFC OFF             |
| DYNAMIC_VOLUME_LIGHT                                | PSDYNVOL LIT          |
| DYNAMIC_VOLUME_MEDIUM                               | PSDYNVOL MED          |
| DYNAMIC_VOLUME_HEAVY                                | PSDYNVOL HEV          |
| CONTAINMENT_AMOUNT_UP                               | PSCNTAMT UP           |
| CONTAINMENT_AMOUNT_DOWN                             | PSCNTAMT DOWN         |
| DIRAC_LIVE_FILTER_SLOT1                             | PSDIRAC 1             |
| DIRAC_LIVE_FILTER_SLOT2                             | PSDIRAC 2             |
| DIRAC_LIVE_FILTER_SLOT3                             | PSDIRAC 3             |
| DIRAC_LIVE_FILTER_OFF                               | PSDIRAC OFF           |

## Known supported devices

Please see the [Home Assistant Denon AVR Network Receivers](https://www.home-assistant.io/integrations/denonavr/)
integration, which uses the same [denonavr](https://github.com/ol-iver/denonavr) communication library.

## Usage

### Setup

- Requires Python 3.11
- Clone the repository with submodules:

```shell
git clone --recursive https://github.com/unfoldedcircle/integration-denonavr.git
```

- Install required libraries:  
  (using a [virtual environment](https://docs.python.org/3/library/venv.html) is highly recommended)

```shell
pip3 install -r requirements.txt
pip3 install ./denonavrlib
```

- The integration is runnable without updating the language files or compiling the .po files!  
  If a language file is missing, the language key is used which in most cases is identical to the English language text.
- Optional: compile gettext translation files:
  - This requires `msgfmt` from the GNU gettext utilities.
  - See [docs/i18n.md](docs/i18n.md) for more information.
  - Helper Makefile:

```shell
cd intg-denonavr/locales
make all
```

For running a separate integration driver on your network for Remote Two/3, the configuration in file
[driver.json](driver.json) needs to be changed:

- Set `driver_id` to a unique value, `uc_denon_driver` is already used for the embedded driver in the firmware.
- Change `name` to easily identify the driver for discovery & setup with Remote Two/3 or the web-configurator.
- Optionally add a `"port": 8090` field for the WebSocket server listening port.
    - Default port: `9090`
    - Also overrideable with environment variable `UC_INTEGRATION_HTTP_PORT`

### Run

```shell
python3 intg-denonavr/driver.py
```

See
available [environment variables](https://github.com/unfoldedcircle/integration-python-library#environment-variables)
in the Python integration library to control certain runtime features like listening interface and configuration
directory.

## Build distribution binary

After some tests, turns out Python stuff on embedded is a nightmare. So we're better off creating a binary distribution
that has everything in it, including the Python runtime and all required modules and native libraries.

To do that, we use [PyInstaller](https://pyinstaller.org/), but it needs to run on the target architecture as
`PyInstaller` does not support cross compilation.

The `--onefile` option to create a one-file bundled executable should be avoided:

- Higher startup cost, since the wrapper binary must first extract the archive.
- Files are extracted to the /tmp directory on the device, which is an in-memory filesystem.  
  This will further reduce the available memory for the integration drivers!

### x86-64 Linux

On x86-64 Linux we need Qemu to emulate the aarch64 target platform:

```bash
sudo apt install qemu-system-arm binfmt-support qemu-user-static
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

Run PyInstaller:

```shell
docker run --rm --name builder \
    --platform=aarch64 \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.13  \
    bash -c \
      "PYTHON_VERSION=\$(python --version | cut -d' ' -f2 | cut -d. -f1,2) && \
      python -m pip install --user -r requirements.txt && \
      python -m pip install --user ./denonavrlib && \
      PYTHONPATH=~/.local/lib/python\${PYTHON_VERSION}/site-packages:\$PYTHONPATH pyinstaller --clean --onedir --name intg-denonavr -y \
        --add-data intg-denonavr/locales:locales intg-denonavr/driver.py"
```

### aarch64 Linux / Mac

On an aarch64 host platform, the build image can be run directly (and much faster):

```shell
docker run --rm --name builder \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.13  \
    bash -c \
      "PYTHON_VERSION=\$(python --version | cut -d' ' -f2 | cut -d. -f1,2) && \
      python -m pip install --user -r requirements.txt && \
      python -m pip install --user ./denonavrlib && \
      PYTHONPATH=~/.local/lib/python\${PYTHON_VERSION}/site-packages:\$PYTHONPATH pyinstaller --clean --onedir --name intg-denonavr -y \
        --add-data intg-denonavr/locales:locales intg-denonavr/driver.py"
```

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the
[tags and releases in this repository](https://github.com/unfoldedcircle/integration-denonavr/releases).

## Changelog

The major changes found in each new release are listed in the [changelog](CHANGELOG.md)
and under the GitHub [releases](https://github.com/unfoldedcircle/integration-denonavr/releases).

## Contributions

Please read our [contribution guidelines](CONTRIBUTING.md) before opening a pull request.

## License

This project is licensed under the [**Mozilla Public License 2.0**](https://choosealicense.com/licenses/mpl-2.0/).
See the [LICENSE](LICENSE) file for details.
