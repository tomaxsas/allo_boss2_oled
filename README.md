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
- Buttons near OLED controls system settings on OLED screens.
- Remote controls play/pause, mute, next, previous and sound volume.
- OLED turns of after 50s of incativity

Tested on Below OS Images:

- Moode 7

Check these?
roPieee, roPieee XL , Dietpi , Volumio, Max2play

## Requirements

- python3-smbus
- python3-alsaaudio
- python3-evdev
- python3-netifaces
- python3
- ir-keytable
- python3-gpiozero

## Installation

- install provided debian package
- reboot

## TODO

- fix alsa sound reset on boot
