# BOSS2 OLED and IR control

Took original Python 2 code. Rewrote most of it.
IR is now controlled by kernel and accessed from python via evdev package.

## Features

- Volume display in dB
- Bit and kHz display
- Filter settings
- RMS voltage control
- Remote control only controls volume, play/pause, mpd next, previous. No OK button functionality
- Buttons near OLED controls system settings.
- OLED turns of after ~50s of incativity

Tested on Below OS Images:

- Rpi OS based on Bookworm

## Requirements

- python3-smbus
- python3-pyalsa
- python3-evdev
- python3-mpd
- python3-netifaces
- python3
- ir-keytable
- python3-gpiozero
- mpd (not hard)

## Installation

- install provided debian package
- reboot

To fix sound state between reboot enable alsa-state:

```bash
sudo touch /etc/alsa/state-daemon.conf
sudo alsactl store
sudo systemctl enable --now alsa-state
sudo systemctl enable --now alsa-restore
``````
