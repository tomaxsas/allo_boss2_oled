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
sudo systemctl start alsa-state
```

### Setup on moOde 9

After installation on moOde 9 and reboot, SSH to to it and run these commands:

```bash
# Stops existing service
sudo systemctl stop boss2oled.service
# Makes that service cannot be started
sudo systemctl mask boss2oled.service
# Starts new service
sudo systemctl enable --now allo_boss2.service
```

## Fine tuning

Noticed that pipewire and wayland (GUI) services uses a lot of CPU when remote control is used. Disable those if not using.
