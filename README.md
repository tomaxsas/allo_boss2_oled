# BOSS2 OLED and IR control

Took original Python 2 code. Rewrote most of it.
IR is now controlled by kernel and accessed from python via evdev package.

## Features

- Volume display (0-100)
- Bit nad kHz display
- Volume settings
- Filter settings
- RMS voltage control
- Remote control only controls volume, play/pause, mpd next, previous. No OK button functionality
- Buttons near OLED only controls system settings, OLED screens.

Tested on Below OS Images:

- Moode

Check these?
roPieee, roPieee XL ,Moode , Dietpi , Volumio, Max2play

## Requirements

- python3-smbus
- python3-alsaaudio
- python3-evdev
- python3-netifaces
- python3
- ir-keytable
- ?python3-wrapt

## Installation

- install provided debian package
- reboot

## TODO

- add to /boot/config.txt: dtoverlay=gpio-ir,gpio_pin=16
- make a deb pkg
- location of toml: /etc/rc_keymaps/
- add services, start irsetup on boot
- fix alsa sound reset on boot
