# BOSS2 OLED and IR control

Took original Python 2 code. Rewrote most of it.
IR is now controlled by kernel and accessed from python via evdev package.

## Features

- Volume display (0-100)
- Bit and kHz display
- Volume settings
- Filter settings
- RMS voltage control
- Remote control only controls volume, play/pause, mpd next, previous. No OK button functionality
- Buttons near OLED controls system settings.
- OLED turns of after 50s of incativity

Tested on Below OS Images:

- Moode 8

Check these?
roPieee, roPieee XL , Dietpi , Volumio, Max2play

## Requirements

- python3-smbus
- python3-pyalsa
- python3-evdev
- python3-netifaces
- python3
- ir-keytable
- python3-gpiozero
- mpd

## Installation

- install provided debian package
- reboot

To fix sound state between reboot enable alsa-state: `sudo systemctl enable --now alsa-state`

## TODO

- Fix CPU usage
