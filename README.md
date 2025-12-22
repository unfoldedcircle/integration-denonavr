# Denon AVR integration for Remote Two/3

Using a forked [denonavr](https://github.com/henrikwidlund/denonavr) library
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

| Simple Command                                      | Device Command              | Manufacturer |
|-----------------------------------------------------|-----------------------------|--------------|
| OUTPUT_1                                            | VSMONI1                     | All          |
| OUTPUT_2                                            | VSMONI2                     | All          |
| OUTPUT_AUTO                                         | VSMONIAUTO                  | All          |
| DIMMER_TOGGLE                                       | DIM SEL                     | All          |
| DIMMER_BRIGHT                                       | DIM BRI                     | All          |
| DIMMER_DIM                                          | DIM DIM                     | All          |
| DIMMER_DARK                                         | DIM DAR                     | All          |
| DIMMER_OFF                                          | DIM OFF                     | All          |
| TRIGGER1_ON                                         | TR1 ON                      | All          |
| TRIGGER1_OFF                                        | TR1 OFF                     | All          |
| TRIGGER2_ON                                         | TR2 ON                      | All          |
| TRIGGER2_OFF                                        | TR2 OFF                     | All          |
| TRIGGER3_ON                                         | TR2 ON                      | All          |
| TRIGGER3_OFF                                        | TR2 OFF                     | All          |
| DELAY_UP                                            | PSDELAY UP                  | All          |
| DELAY_DOWN                                          | PSDELAY DOWN                | All          |
| ECO_AUTO                                            | ECOAUTO                     | All          |
| ECO_ON                                              | ECOON                       | All          |
| ECO_OFF                                             | ECOOFF                      | All          |
| INFO_MENU                                           | MNINF                       | All          |
| CHANNEL_LEVEL_ADJUST_MENU                           | MNCHL                       | All          |
| AUTO_STANDBY_OFF                                    | STBYOFF                     | All          |
| AUTO_STANDBY_15MIN                                  | STBY15M                     | All          |
| AUTO_STANDBY_30MIN                                  | STBY30M                     | All          |
| AUTO_STANDBY_60MIN                                  | STBY60M                     | All          |
| DELAY_TIME_UP                                       | PSDEL UP                    | All          |
| DELAY_TIME_DOWN                                     | PSDEL DOWN                  | All          |
| HDMI_AUDIO_DECODE_AMP                               | VSAUDIO AMP                 | All          |
| HDMI_AUDIO_DECODE_TV                                | VSAUDIO TV                  | All          |
| VIDEO_PROCESSING_MODE_AUTO                          | VSVPMAUTO                   | All          |
| VIDEO_PROCESSING_MODE_GAME                          | VSVPMGAME                   | All          |
| VIDEO_PROCESSING_MODE_MOVIE                         | VSVPMOVI                    | All          |
| VIDEO_PROCESSING_MODE_BYPASS                        | VSVPMBYP                    | All          |
| NETWORK_RESTART                                     | NSRBT                       | All          |
| SPEAKER_PRESET_1                                    | SPPR 1                      | All          |
| SPEAKER_PRESET_2                                    | SPPR 2                      | All          |
| SPEAKER_PRESET_TOGGLE                               | SPPR 1/2                    | All          |
| BT_TRANSMITTER_ON                                   | BTTX ON                     | All          |
| BT_TRANSMITTER_OFF                                  | BTTX OFF                    | All          |
| BT_TRANSMITTER_TOGGLE                               | BTTX ON/OFF                 | All          |
| BT_OUTPUT_MODE_BT_SPEAKER                           | BTTX SP                     | All          |
| BT_OUTPUT_MODE_BT_ONLY                              | BTTX BT                     | All          |
| BT_OUTPUT_MODE_TOGGLE                               | BTTX SP/BT                  | All          |
| AUDIO_RESTORER_OFF                                  | PSRSTR OFF                  | All          |
| AUDIO_RESTORER_LOW                                  | PSRSTR LOW                  | All          |
| AUDIO_RESTORER_MEDIUM                               | PSRSTR MED                  | All          |
| AUDIO_RESTORER_HIGH                                 | PSRSTR HI                   | All          |
| REMOTE_CONTROL_LOCK_ON                              | SYREMOTE LOCK ON            | All          |
| REMOTE_CONTROL_LOCK_OFF                             | SYREMOTE LOCK OFF           | All          |
| PANEL_LOCK_PANEL                                    | SYPANEL LOCK ON             | All          |
| PANEL_LOCK_PANEL_VOLUME                             | SYPANEL+V LOCK ON           | All          |
| PANEL_LOCK_OFF                                      | SYPANEL LOCK OFF            | All          |
| GRAPHIC_EQ_ON                                       | PSGEQ ON                    | All          |
| GRAPHIC_EQ_OFF                                      | PSGEQ OFF                   | All          |
| GRAPHIC_EQ_TOGGLE                                   | PSGEQ ON/OFF                | All          |
| HEADPHONE_EQ_ON                                     | PSHEQ ON                    | All          |
| HEADPHONE_EQ_OFF                                    | PSHEQ OFF                   | All          |
| HEADPHONE_EQ_TOGGLE                                 | PSHEQ ON/OFF                | All          |
| STATUS                                              | RCSHP0230030                | Denon        |
| INPUT_PHONO                                         | SIPHONO                     | All          |
| INPUT_CD                                            | SICD                        | All          |
| INPUT_DVD                                           | SIDVD                       | All          |
| INPUT_BD                                            | SIBD                        | All          |
| INPUT_TV                                            | SITV                        | All          |
| INPUT_SAT_CBL                                       | SISAT/CBL                   | All          |
| INPUT_MPLAY                                         | SIMPLAY                     | All          |
| INPUT_GAME                                          | SIGAME                      | All          |
| INPUT_GAME1                                         | SIGAME1                     | All          |
| INPUT_GAME2                                         | SIGAME2                     | All          |
| INPUT_TUNER                                         | SITUNER                     | All          |
| INPUT_8K                                            | SI8K                        | All          |
| INPUT_AUX1                                          | SIAUX1                      | All          |
| INPUT_AUX2                                          | SIAUX2                      | All          |
| INPUT_AUX3                                          | SIAUX3                      | All          |
| INPUT_AUX4                                          | SIAUX4                      | All          |
| INPUT_AUX5                                          | SIAUX5                      | All          |
| INPUT_AUX6                                          | SIAUX6                      | All          |
| INPUT_AUX7                                          | SIAUX7                      | All          |
| INPUT_NET                                           | SINET                       | All          |
| INPUT_BT                                            | SIBT                        | All          |
| INPUT_HD_RADIO                                      | SIHDRADIO                   | All          |
| HDMI_CEC_ON                                         | RCKSK0410826 / RCRC51608408 | All          |
| HDMI_CEC_OFF                                        | RCKSK0410827 / RCRC51608409 | All          |
| QUICK_SELECT_1                                      | MSQUICK1                    | Denon        |
| QUICK_SELECT_2                                      | MSQUICK2                    | Denon        |
| QUICK_SELECT_3                                      | MSQUICK3                    | Denon        |
| QUICK_SELECT_4                                      | MSQUICK4                    | Denon        |
| QUICK_SELECT_5                                      | MSQUICK5                    | Denon        |
| SMART_SELECT_1                                      | MSSMART1                    | Marantz      |
| SMART_SELECT_2                                      | MSSMART2                    | Marantz      |
| SMART_SELECT_3                                      | MSSMART3                    | Marantz      |
| SMART_SELECT_4                                      | MSSMART4                    | Marantz      |
| SMART_SELECT_5                                      | MSSMART5                    | Marantz      |
| ILLUMINATION_AUTO                                   | ILB AUTO                    | Marantz      |
| ILLUMINATION_BRIGHT                                 | ILB BRI                     | Marantz      |
| ILLUMINATION_DIM                                    | ILB DIM                     | Marantz      |
| ILLUMINATION_DARK                                   | ILB DAR                     | Marantz      |
| ILLUMINATION_OFF                                    | ILB OFF                     | Marantz      |
| AUTO_LIP_SYNC_ON                                    | SSHOSALS ON                 | Marantz      |
| AUTO_LIP_SYNC_OFF                                   | SSHOSALS OFF                | Marantz      |
| FRONT_LEFT_UP                                       | CVFL UP                     | All          |
| FRONT_LEFT_DOWN                                     | CVFL DOWN                   | All          |
| FRONT_RIGHT_UP                                      | CVFR UP                     | All          |
| FRONT_RIGHT_DOWN                                    | CVFR DOWN                   | All          |
| CENTER_UP                                           | CVC UP                      | All          |
| CENTER_DOWN                                         | CVC DOWN                    | All          |
| SUB1_UP                                             | CVSW UP                     | All          |
| SUB1_DOWN                                           | CVSW DOWN                   | All          |
| SUB2_UP                                             | CVSW2 UP                    | All          |
| SUB2_DOWN                                           | CVSW2 DOWN                  | All          |
| SUB3_UP                                             | CVSW3 UP                    | All          |
| SUB3_DOWN                                           | CVSW3 DOWN                  | All          |
| SUB4_UP                                             | CVSW4 UP                    | All          |
| SUB4_DOWN                                           | CVSW4 DOWN                  | All          |
| SURROUND_LEFT_UP                                    | CVSL UP                     | All          |
| SURROUND_LEFT_DOWN                                  | CVSL DOWN                   | All          |
| SURROUND_RIGHT_UP                                   | CVSR UP                     | All          |
| SURROUND_RIGHT_DOWN                                 | CVSR DOWN                   | All          |
| SURROUND_BACK_LEFT_UP                               | CVSBL UP                    | All          |
| SURROUND_BACK_LEFT_DOWN                             | CVSBL DOWN                  | All          |
| SURROUND_BACK_RIGHT_UP                              | CVSBR UP                    | All          |
| SURROUND_BACK_RIGHT_DOWN                            | CVSBR DOWN                  | All          |
| FRONT_HEIGHT_LEFT_UP                                | CVFHL UP                    | All          |
| FRONT_HEIGHT_LEFT_DOWN                              | CVFHL DOWN                  | All          |
| FRONT_HEIGHT_RIGHT_UP                               | CVFHR UP                    | All          |
| FRONT_HEIGHT_RIGHT_DOWN                             | CVFHR DOWN                  | All          |
| FRONT_WIDE_LEFT_UP                                  | CVFWL UP                    | All          |
| FRONT_WIDE_LEFT_DOWN                                | CVFWL DOWN                  | All          |
| FRONT_WIDE_RIGHT_UP                                 | CVFWR UP                    | All          |
| FRONT_WIDE_RIGHT_DOWN                               | CVFWR DOWN                  | All          |
| TOP_FRONT_LEFT_UP                                   | CVTFL UP                    | All          |
| TOP_FRONT_LEFT_DOWN                                 | CVTFL DOWN                  | All          |
| TOP_FRONT_RIGHT_UP                                  | CVTFR UP                    | All          |
| TOP_FRONT_RIGHT_DOWN                                | CVTFR DOWN                  | All          |
| TOP_MIDDLE_LEFT_UP                                  | CVTML UP                    | All          |
| TOP_MIDDLE_LEFT_DOWN                                | CVTML DOWN                  | All          |
| TOP_MIDDLE_RIGHT_UP                                 | CVTMR UP                    | All          |
| TOP_MIDDLE_RIGHT_DOWN                               | CVTMR DOWN                  | All          |
| TOP_REAR_LEFT_UP                                    | CVTRL UP                    | All          |
| TOP_REAR_LEFT_DOWN                                  | CVTRL DOWN                  | All          |
| TOP_REAR_RIGHT_UP                                   | CVTRR UP                    | All          |
| TOP_REAR_RIGHT_DOWN                                 | CVTRR DOWN                  | All          |
| REAR_HEIGHT_LEFT_UP                                 | CVRHL UP                    | All          |
| REAR_HEIGHT_LEFT_DOWN                               | CVRHL DOWN                  | All          |
| REAR_HEIGHT_RIGHT_UP                                | CVRHR UP                    | All          |
| REAR_HEIGHT_RIGHT_DOWN                              | CVRHR DOWN                  | All          |
| FRONT_DOLBY_LEFT_UP                                 | CVFDL UP                    | All          |
| FRONT_DOLBY_LEFT_DOWN                               | CVFDL DOWN                  | All          |
| FRONT_DOLBY_RIGHT_UP                                | CVFDR UP                    | All          |
| FRONT_DOLBY_RIGHT_DOWN                              | CVFDR DOWN                  | All          |
| SURROUND_DOLBY_LEFT_UP                              | CVSDL UP                    | All          |
| SURROUND_DOLBY_LEFT_DOWN                            | CVSDL DOWN                  | All          |
| SURROUND_DOLBY_RIGHT_UP                             | CVSDR UP                    | All          |
| SURROUND_DOLBY_RIGHT_DOWN                           | CVSDR DOWN                  | All          |
| BACK_DOLBY_LEFT_UP                                  | CVBDL UP                    | All          |
| BACK_DOLBY_LEFT_DOWN                                | CVBDL DOWN                  | All          |
| BACK_DOLBY_RIGHT_UP                                 | CVBDR UP                    | All          |
| BACK_DOLBY_RIGHT_DOWN                               | CVBDR DOWN                  | All          |
| SURROUND_HEIGHT_LEFT_UP                             | CVSHL UP                    | All          |
| SURROUND_HEIGHT_LEFT_DOWN                           | CVSHL DOWN                  | All          |
| SURROUND_HEIGHT_RIGHT_UP                            | CVSHR UP                    | All          |
| SURROUND_HEIGHT_RIGHT_DOWN                          | CVSHR DOWN                  | All          |
| TOP_SURROUND_UP                                     | CVTS UP                     | All          |
| TOP_SURROUND_DOWN                                   | CVTS DOWN                   | All          |
| CENTER_HEIGHT_UP                                    | CVCH UP                     | All          |
| CENTER_HEIGHT_DOWN                                  | CVCH DOWN                   | All          |
| CHANNEL_VOLUMES_RESET                               | CVZRL                       | All          |
| SUBWOOFER_ON                                        | PSSWR ON                    | All          |
| SUBWOOFER_OFF                                       | PSSWR OFF                   | All          |
| SUBWOOFER_TOGGLE                                    | PSSWR ON/OFF                | All          |
| SUBWOOFER1_LEVEL_UP                                 | PSSWL UP                    | All          |
| SUBWOOFER1_LEVEL_DOWN                               | PSSWL DOWN                  | All          |
| SUBWOOFER2_LEVEL_UP                                 | PSSWL2 UP                   | All          |
| SUBWOOFER2_LEVEL_DOWN                               | PSSWL2 DOWN                 | All          |
| SUBWOOFER3_LEVEL_UP                                 | PSSWL3 UP                   | All          |
| SUBWOOFER3_LEVEL_DOWN                               | PSSWL3 DOWN                 | All          |
| SUBWOOFER4_LEVEL_UP                                 | PSSWL4 UP                   | All          |
| SUBWOOFER4_LEVEL_DOWN                               | PSSWL4 DOWN                 | All          |
| LFE_UP                                              | PSLFE UP                    | All          |
| LFE_DOWN                                            | PSLFE DOWN                  | All          |
| BASS_SYNC_UP                                        | PSBSC UP                    | All          |
| BASS_SYNC_DOWN                                      | PSBSC DOWN                  | All          |
| SURROUND_MODE_AUTO                                  | MSAUTO                      | All          |
| SURROUND_MODE_DIRECT                                | MSDIRECT                    | All          |
| SURROUND_MODE_PURE_DIRECT                           | MSPURE DIRECT               | All          |
| SURROUND_MODE_DOLBY_DIGITAL                         | MSDOLBY DIGITAL             | All          |
| SURROUND_MODE_DTS_SURROUND                          | MSDTS SURROUND              | All          |
| SURROUND_MODE_AURO3D                                | MSAURO3D                    | All          |
| SURROUND_MODE_AURO2DSURR                            | MSAURO2DSURR                | All          |
| SURROUND_MODE_MCH_STEREO                            | MSMCH STEREO                | All          |
| SURROUND_MODE_NEXT                                  | MSRIGHT                     | All          |
| SURROUND_MODE_PREVIOUS                              | MSLEFT                      | All          |
| SOUND_MODE_NEURAL_X_ON                              | PSNEURAL ON                 | All          |
| SOUND_MODE_NEURAL_X_OFF                             | PSNEURAL OFF                | All          |
| SOUND_MODE_NEURAL_X_TOGGLE                          | PSNEURAL ON/OFF             | All          |
| SOUND_MODE_IMAX_AUTO                                | PSIMAX AUTO                 | All          |
| SOUND_MODE_IMAX_OFF                                 | PSIMAX OFF                  | All          |
| SOUND_MODE_IMAX_TOGGLE                              | PSIMAX AUTO/OFF             | All          |
| IMAX_AUDIO_SETTINGS_AUTO                            | PSIMAXAUD AUTO              | All          |
| IMAX_AUDIO_SETTINGS_MANUAL                          | PSIMAXAUD MANUAL            | All          |
| IMAX_AUDIO_SETTINGS_TOGGLE                          | PSIMAXAUD AUTO/MANUAL       | All          |
| IMAX_HPF_40HZ                                       | PSIMAXHPF 40                | All          |
| IMAX_HPF_60HZ                                       | PSIMAXHPF 60                | All          |
| IMAX_HPF_80HZ                                       | PSIMAXHPF 80                | All          |
| IMAX_HPF_90HZ                                       | PSIMAXHPF 90                | All          |
| IMAX_HPF_100HZ                                      | PSIMAXHPF 100               | All          |
| IMAX_HPF_110HZ                                      | PSIMAXHPF 110               | All          |
| IMAX_HPF_120HZ                                      | PSIMAXHPF 120               | All          |
| IMAX_HPF_150HZ                                      | PSIMAXHPF 150               | All          |
| IMAX_HPF_180HZ                                      | PSIMAXHPF 180               | All          |
| IMAX_HPF_200HZ                                      | PSIMAXHPF 200               | All          |
| IMAX_HPF_250HZ                                      | PSIMAXHPF 250               | All          |
| IMAX_LPF_80HZ                                       | PSIMAXLPF 80                | All          |
| IMAX_LPF_90HZ                                       | PSIMAXLPF 90                | All          |
| IMAX_LPF_100HZ                                      | PSIMAXLPF 100               | All          |
| IMAX_LPF_110HZ                                      | PSIMAXLPF 110               | All          |
| IMAX_LPF_120HZ                                      | PSIMAXLPF 120               | All          |
| IMAX_LPF_150HZ                                      | PSIMAXLPF 150               | All          |
| IMAX_LPF_180HZ                                      | PSIMAXLPF 180               | All          |
| IMAX_LPF_200HZ                                      | PSIMAXLPF 200               | All          |
| IMAX_LPF_250HZ                                      | PSIMAXLPF 250               | All          |
| IMAX_SUBWOOFER_ON                                   | PSIMAXSWM ON                | All          |
| IMAX_SUBWOOFER_OFF                                  | PSIMAXSWM OFF               | All          |
| IMAX_SUBWOOFER_OUTPUT_LFE_MAIN                      | PSIMAXSWO L+M               | All          |
| IMAX_SUBWOOFER_OUTPUT_LFE                           | PSIMAXSWO LFE               | All          |
| CINEMA_EQ_ON                                        | PSCINEMA EQ.ON              | All          |
| CINEMA_EQ_OFF                                       | PSCINEMA EQ.OFF             | All          |
| CINEMA_EQ_TOGGLE                                    | PSCINEMA EQ.ON/OFF          | All          |
| CENTER_SPREAD_ON                                    | PSCES ON                    | All          |
| CENTER_SPREAD_OFF                                   | PSCES OFF                   | All          |
| CENTER_SPREAD_TOGGLE                                | PSCES ON/OFF                | All          |
| LOUDNESS_MANAGEMENT_ON                              | PSLOM ON                    | All          |
| LOUDNESS_MANAGEMENT_OFF                             | PSLOM OFF                   | All          |
| LOUDNESS_MANAGEMENT_TOGGLE                          | PSLOM ON/OFF                | All          |
| DIALOG_ENHANCER_OFF                                 | PSDEH OFF                   | All          |
| DIALOG_ENHANCER_LOW                                 | PSDEH LOW                   | All          |
| DIALOG_ENHANCER_MEDIUM                              | PSDEH MED                   | All          |
| DIALOG_ENHANCER_HIGH                                | PSDEH HIGH                  | All          |
| AUROMATIC_3D_PRESET_SMALL                           | PSAUROPR SMA                | All          |
| AUROMATIC_3D_PRESET_MEDIUM                          | PSAUROPR MED                | All          |
| AUROMATIC_3D_PRESET_LARGE                           | PSAUROPR LAR                | All          |
| AUROMATIC_3D_PRESET_SPEECH                          | PSAUROPR SPE                | All          |
| AUROMATIC_3D_PRESET_MOVIE                           | PSAUROPR MOV                | All          |
| AUROMATIC_3D_STRENGTH_UP                            | PSAUROST UP                 | All          |
| AUROMATIC_3D_STRENGTH_DOWN                          | PSAUROST DOWN               | All          |
| AURO_3D_MODE_DIRECT                                 | PSAUROMODE DRCT             | All          |
| AURO_3D_MODE_CHANNEL_EXPANSION                      | PSAUROMODE EXP              | All          |
| DIALOG_CONTROL_UP                                   | PSDIC UP                    | All          |
| DIALOG_CONTROL_DOWN                                 | PSDIC DOWN                  | All          |
| SPEAKER_VIRTUALIZER_ON                              | PSSPV ON                    | All          |
| SPEAKER_VIRTUALIZER_OFF                             | PSSPV OFF                   | All          |
| SPEAKER_VIRTUALIZER_TOGGLE                          | PSSPV ON/OFF                | All          |
| EFFECT_SPEAKER_SELECTION_FLOOR                      | PSSP:FL                     | All          |
| EFFECT_SPEAKER_SELECTION_FRONT                      | PSSP:FR                     | All          |
| EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT               | PSSP:FH                     | All          |
| EFFECT_SPEAKER_SELECTION_FRONT_WIDE                 | PSSP:FW                     | All          |
| EFFECT_SPEAKER_SELECTION_FRONT_HEIGHT_WIDE          | PSSP:HW                     | All          |
| EFFECT_SPEAKER_SELECTION_HEIGHT_FLOOR               | PSSP:HF                     | All          |
| EFFECT_SPEAKER_SELECTION_SURROUND_BACK              | PSSP:SB                     | All          |
| EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_HEIGHT | PSSP:BH                     | All          |
| EFFECT_SPEAKER_SELECTION_SURROUND_BACK_FRONT_WIDE   | PSSP:BW                     | All          |
| DRC_AUTO                                            | PSDRC AUTO                  | All          |
| DRC_LOW                                             | PSDRC LOW                   | All          |
| DRC_MID                                             | PSDRC MID                   | All          |
| DRC_HI                                              | PSDRC HI                    | All          |
| DRC_OFF                                             | PSDRC OFF                   | All          |
| MDAX_OFF                                            | PSMDAX OFF                  | All          |
| MDAX_LOW                                            | PSMDAX LOW                  | All          |
| MDAX_MEDIUM                                         | PSMDAX MED                  | All          |
| MDAX_HIGH                                           | PSMDAX HI                   | All          |
| DAC_FILTER_MODE_1                                   | PSDACFIL MODE1              | All          |
| DAC_FILTER_MODE_2                                   | PSDACFIL MODE2              | All          |
| MULTIEQ_REFERENCE                                   | PSMULTEQ:AUDYSSEY           | All          |
| MULTIEQ_BYPASS_LR                                   | MULTEQ:BYP.LR               | All          |
| MULTIEQ_FLAT                                        | PSMULTEQ:FLAT               | All          |
| MULTIEQ_OFF                                         | PSMULTEQ:OFF                | All          |
| DYNAMIC_EQ_ON                                       | PSDYNEQ ON                  | All          |
| DYNAMIC_EQ_OFF                                      | PSDYNEQ OFF                 | All          |
| DYNAMIC_EQ_TOGGLE                                   | PSDYNEQ ON/OFF              | All          |
| DYNAMIC_VOLUME_OFF                                  | PSDYNVOL OFF                | All          |
| AUDYSSEY_LFC                                        | PSLFC ON                    | All          |
| AUDYSSEY_LFC_OFF                                    | PSLFC OFF                   | All          |
| AUDYSSEY_LFC_TOGGLE                                 | PSLFC ON/OFF                | All          |
| DYNAMIC_VOLUME_LIGHT                                | PSDYNVOL LIT                | All          |
| DYNAMIC_VOLUME_MEDIUM                               | PSDYNVOL MED                | All          |
| DYNAMIC_VOLUME_HEAVY                                | PSDYNVOL HEV                | All          |
| CONTAINMENT_AMOUNT_UP                               | PSCNTAMT UP                 | All          |
| CONTAINMENT_AMOUNT_DOWN                             | PSCNTAMT DOWN               | All          |
| DIRAC_LIVE_FILTER_SLOT1                             | PSDIRAC 1                   | All          |
| DIRAC_LIVE_FILTER_SLOT2                             | PSDIRAC 2                   | All          |
| DIRAC_LIVE_FILTER_SLOT3                             | PSDIRAC 3                   | All          |
| DIRAC_LIVE_FILTER_OFF                               | PSDIRAC OFF                 | All          |

## Known supported devices

Please see the [Home Assistant Denon AVR Network Receivers](https://www.home-assistant.io/integrations/denonavr/)
integration, which uses the same [denonavr](https://github.com/ol-iver/denonavr) communication library.

## Usage

### Setup

- Requires Python 3.11

- Install required libraries:  
  (using a [virtual environment](https://docs.python.org/3/library/venv.html) is highly recommended)

```shell
pip3 install -r requirements.txt
```

When updating from an older version, it might be required to reinstall the libraries (because the forked `denonavr`
library was moved from a Git submodule to a regular GitHub dependency):
```shell
pip install --upgrade --force-reinstall -r requirements.txt
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
`PyInstaller` does not support cross-compilation.

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
