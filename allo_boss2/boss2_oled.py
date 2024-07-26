#!/usr/bin/python3
"""
Copyright 2020 allo.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import sched
import signal
import socket
import subprocess
import sys
import threading
import time
from enum import Enum

import netifaces
from evdev import InputDevice, ecodes, list_devices
from gpiozero import Button, Device
from gpiozero.pins.rpigpio import RPiGPIOFactory
from allo_boss2.Hardware.SH1106.SH1106LCD import SH1106LCD
from allo_boss2.persistent_mpd import PersistentMPDClient
from pyalsa import alsacard, alsamixer

# Force to use RPi pin factory
Device.pin_factory = RPiGPIOFactory()


# Use BCM pin numbering scheme
class SW_PIN(Enum):
    LEFT = 14
    OK = 15
    UP = 23
    DOWN = 8
    RIGHT = 24


try:
    ETH_IP = netifaces.ifaddresses("eth0")[2][0]["addr"]
except Exception:
    ETH_IP = ""
try:
    WLAN_IP = netifaces.ifaddresses("wlan0")[2][0]["addr"]
except Exception:
    WLAN_IP = ""


class SCREEN(Enum):
    MAIN = 0
    BOOT = 1
    MENU = 2
    FILTER = 3
    HV = 4
    SP = 5
    HP = 6
    DE = 6
    NON = 8
    PH = 9


def db_show_vol(vol_db):
    if vol_db % 100 == 0:
        vol_list = int(vol_db / 100)
    else:
        vol_list = vol_db / 100
    return vol_list


class SOUND_CTRL:
    def __init__(self):
        self.card_num = self.getCardNumber()

        self.mixer = alsamixer.Mixer()
        self.mixer.attach("hw:%d" % self.card_num)
        self.mixer.load()

        # setup mixers:
        self.de_ctrl = alsamixer.Element(
            mixer=self.mixer, name="PCM De-emphasis Filter", index=0
        )
        self.hp_ctrl = alsamixer.Element(
            mixer=self.mixer, name="PCM High-pass Filter", index=0
        )
        self.ph_ctrl = alsamixer.Element(
            mixer=self.mixer, name="PCM Phase Compensation", index=0
        )
        self.non_ctrl = alsamixer.Element(
            mixer=self.mixer, name="PCM Nonoversample Emulate", index=0
        )
        self.hv_ctrl = alsamixer.Element(mixer=self.mixer, name="HV_Enable", index=0)
        self.sp_ctrl = alsamixer.Element(
            mixer=self.mixer, name="PCM Filter Speed", index=0
        )
        self.ma_ctrl = alsamixer.Element(mixer=self.mixer, name="Master", index=0)
        self.dig_ctrl = alsamixer.Element(mixer=self.mixer, name="Digital", index=0)

    def change_mute_status(self, mix: alsamixer.Element):
        mute_status = mix.get_switch(0, False)
        mix.set_switch_all(not mute_status)

    # Return True for unmute False for mute
    def get_mute_status(self, mix: alsamixer.Element) -> bool:
        mute_status = mix.get_switch(0, False)
        return mute_status

    def getCardNumber(self):
        sound_cards = alsacard.card_list()
        for sound_card in sound_cards:
            if "Allo Boss2" == alsacard.card_get_name(card=sound_card):
                return sound_card
        print("no boss2 card detected")
        exit(0)

    # Return True for speed False for slow
    def getFilterStatus(self) -> bool:
        cmd = f"amixer -c {self.card_num} get 'PCM Filter Speed' | grep Item0"
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, _ = proc.communicate()
        word_str = out.decode().split()
        current_status = word_str[1]
        return current_status != "'Slow'"

    def changeFilterStatus(self):
        if self.getFilterStatus():
            cmd = f"amixer -c {self.card_num} set 'PCM Filter Speed' Slow"
        else:
            cmd = f"amixer -c {self.card_num} set 'PCM Filter Speed' Fast"
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        proc.communicate()


class OLED:
    _h_name = f"HOST: {socket.gethostname()}"

    def __init__(self, card_num, snd_ctrl: SOUND_CTRL):
        self.oled = SH1106LCD()
        self.t_lock = threading.Lock()
        self.current_screen = SCREEN.MAIN
        self.current_hw_line = ""
        self.oled.powerUp()
        self.oled.clearScreen()
        self.card_num = card_num
        self.m_indx = 1
        self.f_indx = 1
        self.ok_flag = False

        self.hp_fil = snd_ctrl.get_mute_status(snd_ctrl.hp_ctrl)
        self.hv_en = snd_ctrl.get_mute_status(snd_ctrl.hv_ctrl)
        self.non_os = snd_ctrl.get_mute_status(snd_ctrl.non_ctrl)
        self.ph_comp = snd_ctrl.get_mute_status(snd_ctrl.ph_ctrl)
        self.de_emp = snd_ctrl.get_mute_status(snd_ctrl.de_ctrl)
        self.filter_cur = snd_ctrl.getFilterStatus()
        self.fil_sp = self.filter_cur

        self.led_off_counter = 0
        self.snd_ctrl = snd_ctrl

    def _check_screen(self, scr: SCREEN):
        if self.current_screen != scr:
            self.oled.clearScreen()
            self.current_hw_line = ""
        self.current_screen = scr

    def boot_screen(self):
        self._check_screen(SCREEN.BOOT)
        with self.t_lock:
            self.oled.clearScreen()
            self.oled.displayString("BOSS2", 0, 0)
            self.oled.displayStringNumber(ETH_IP, 2, 0)
            # SHowing 13 Chars of hostname
            self.oled.displayString(str(self._h_name[:13]), 4, 0)
            self.oled.displayStringNumber(WLAN_IP, 6, 0)

    def volume_line(self, volume=None):
        if self.current_screen == SCREEN.MAIN:
            if volume is None:
                self.snd_ctrl.mixer.handle_events()
                volume = self.snd_ctrl.ma_ctrl.get_volume()
            vol_list = db_show_vol(self.snd_ctrl.ma_ctrl.ask_volume_dB(volume))
            with self.t_lock:
                self.oled.displayString("     ", 1, 2)
                self.oled.displayString(f"  {vol_list}".ljust(8, " ") + "dB", 1, 1)

    def mute_line(self):
        if self.current_screen == SCREEN.MAIN:
            with self.t_lock:
                if self.snd_ctrl.get_mute_status(self.snd_ctrl.ma_ctrl):
                    self.oled.displayString("  ", 3, 50)
                else:
                    self.oled.displayString("@", 3, 50)

    def hw_line(self):
        bit_rate = "closed"
        bit_format = 0
        if self.current_screen == SCREEN.MAIN:
            with open(
                f"/proc/asound/card{self.card_num}/pcm0p/sub0/hw_params"
            ) as hw_params:
                for line in hw_params:
                    if line.startswith("format:"):
                        format_val = line.split(":")
                        bit_rate = format_val[1].strip()[1:3]
                    if line.startswith("rate:"):
                        rate_val = line.split(":")
                        bit_format = int(rate_val[1].strip().split()[0])
            if bit_rate == "closed":
                hw_line = "No stream"
            else:
                hw_line = f"S{bit_rate} {bit_format}"
            if self.current_hw_line != hw_line:
                self.led_off_counter = 0
                self.current_hw_line = hw_line
                with self.t_lock:
                    self.oled.displayString("                  ", 5, 5)
                    self.oled.displayString(hw_line, 5, 5)

    def volume_screen(self):
        self._check_screen(SCREEN.MAIN)
        self.volume_line()
        self.mute_line()
        self.hw_line()

    def menu_screen(self):
        self._check_screen(SCREEN.MENU)
        if self.m_indx == 1:
            self.oled.displayInvertedString("SYSINFO", 0, 0)
        else:
            self.oled.displayString("SYSINFO", 0, 0)
        if self.m_indx == 2:
            if self.hv_en:
                self.oled.displayInvertedString("HV-EN ON", 2, 0)
            else:
                self.oled.displayInvertedString("HV-EN OFF", 2, 0)
        else:
            if self.hv_en:
                self.oled.displayString("HV-EN ON", 2, 0)
            else:
                self.oled.displayString("HV-EN OFF", 2, 0)
        if self.m_indx == 3:
            self.oled.displayInvertedString("FILTER", 4, 0)
        else:
            self.oled.displayString("FILTER", 4, 0)
        if self.m_indx == 4:
            if self.fil_sp:
                self.oled.displayInvertedString("F-SPEED-FAS", 6, 0)
            else:
                self.oled.displayInvertedString("F-SPEED-SLO", 6, 0)
        else:
            if self.fil_sp:
                self.oled.displayString("F-SPEED-FAS", 6, 0)
            else:
                self.oled.displayString("F-SPEED-SLO", 6, 0)

    def filter_screen(self):
        self._check_screen(SCREEN.FILTER)
        if self.f_indx == 1:
            self.oled.displayInvertedString("PHCOMP ", 0, 5)
            self.oled.displayInvertedString("| ", 0, 64)
            if self.ph_comp:
                self.oled.displayInvertedString("EN", 0, 80)
            else:
                self.oled.displayInvertedString("DIS", 0, 80)
        else:
            self.oled.displayString("PHCOMP ", 0, 5)
            self.oled.displayString("| ", 0, 64)
            if self.ph_comp:
                self.oled.displayString("EN", 0, 80)
            else:
                self.oled.displayString("DIS", 0, 80)

        if self.f_indx == 2:
            self.oled.displayInvertedString("HP-FIL ", 2, 5)
            self.oled.displayInvertedString("| ", 2, 64)
            if self.hp_fil:
                self.oled.displayInvertedString("EN", 2, 80)
            else:
                self.oled.displayInvertedString("DIS", 2, 80)
        else:
            self.oled.displayString("HP-FIL ", 2, 5)
            self.oled.displayString("| ", 2, 64)
            if self.hp_fil:
                self.oled.displayString("EN", 2, 80)
            else:
                self.oled.displayString("DIS", 2, 80)
        if self.f_indx == 3:
            self.oled.displayInvertedString("DE-EMP ", 4, 5)
            self.oled.displayInvertedString("| ", 4, 64)
            if self.de_emp:
                self.oled.displayInvertedString("EN", 4, 80)
            else:
                self.oled.displayInvertedString("DIS", 4, 80)
        else:
            self.oled.displayString("DE-EMP ", 4, 5)
            self.oled.displayString("| ", 4, 64)
            if self.de_emp:
                self.oled.displayString("EN", 4, 80)
            else:
                self.oled.displayString("DIS", 4, 80)
        if self.f_indx == 4:
            self.oled.displayInvertedString("NON-OS ", 6, 5)
            self.oled.displayInvertedString("| ", 6, 64)
            if self.non_os:
                self.oled.displayInvertedString("EN", 6, 80)
            else:
                self.oled.displayInvertedString("DIS", 6, 80)
        else:
            self.oled.displayString("NON-OS ", 6, 5)
            self.oled.displayString("| ", 6, 64)
            if self.non_os:
                self.oled.displayString("EN", 6, 80)
            else:
                self.oled.displayString("DIS", 6, 80)

    def sp_screen(self):
        self._check_screen(SCREEN.SP)
        self.oled.displayString("FILTER SPEED", 0, 5)
        if self.fil_sp:
            self.oled.displayInvertedString("FAST", 3, 10)
            self.oled.displayString("SLOW", 3, 80)
        else:
            self.oled.displayString("FAST", 3, 10)
            self.oled.displayInvertedString("SLOW", 3, 80)
        if self.ok_flag:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def hp_screen(self):
        self._check_screen(SCREEN.HP)
        self.oled.displayString("HP-FILT", 0, 20)
        if self.hp_fil:
            self.oled.displayInvertedString("EN", 3, 10)
            self.oled.displayString("DIS", 3, 70)
        else:
            self.oled.displayString("EN", 3, 10)
            self.oled.displayInvertedString("DIS", 3, 70)
        if self.ok_flag:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def de_screen(self):
        self._check_screen(SCREEN.DE)
        self.oled.displayString("DE-EMPH", 0, 20)
        if self.de_emp:
            self.oled.displayInvertedString("EN", 3, 10)
            self.oled.displayString("DIS", 3, 70)
        else:
            self.oled.displayString("EN", 3, 10)
            self.oled.displayInvertedString("DIS", 3, 70)
        if self.ok_flag:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def non_screen(self):
        self._check_screen(SCREEN.NON)
        self.oled.displayString("NON-OSAMP", 0, 20)
        if self.non_os:
            self.oled.displayInvertedString("EN", 3, 10)
            self.oled.displayString("DIS", 3, 70)
        else:
            self.oled.displayString("EN", 3, 10)
            self.oled.displayInvertedString("DIS", 3, 70)
        if self.ok_flag:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def ph_screen(self):
        self._check_screen(SCREEN.PH)
        self.oled.displayString("PHA-COMP", 0, 20)
        if self.ph_comp:
            self.oled.displayInvertedString("EN", 3, 10)
            self.oled.displayString("DIS", 3, 70)
        else:
            self.oled.displayString("EN", 3, 10)
            self.oled.displayInvertedString("DIS", 3, 70)
        if self.ok_flag:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def hv_screen(self):
        self._check_screen(SCREEN.HV)
        self.oled.displayString("HV ENABLE", 0, 20)
        if self.hv_en:
            self.oled.displayInvertedString("ON", 3, 20)
            self.oled.displayString("OFF", 3, 70)
        else:
            self.oled.displayString("ON", 3, 20)
            self.oled.displayInvertedString("OFF", 3, 70)
        if self.ok_flag:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def sw_left_callback(self):
        if (
            self.current_screen == SCREEN.MAIN
            or self.current_screen == SCREEN.BOOT
            or self.current_screen == SCREEN.MENU
        ):
            self.volume_screen()
        elif self.current_screen == SCREEN.FILTER:
            self.menu_screen()
        elif self.current_screen == SCREEN.HV:
            if not self.hv_en:
                self.hv_en = True
                self.hv_screen()
        elif self.current_screen == SCREEN.SP:
            if not self.fil_sp:
                self.fil_sp = True
                self.sp_screen()
        elif self.current_screen == SCREEN.HP:
            if not self.hp_fil:
                self.hp_fil = True
                self.hp_screen()
        elif self.current_screen == SCREEN.DE:
            if not self.de_emp:
                self.de_emp = True
                self.de_screen()
        elif self.current_screen == SCREEN.NON:
            if not self.non_os:
                self.non_os = True
                self.non_screen()
        elif self.current_screen == SCREEN.PH:
            if not self.ph_comp:
                self.ph_comp = True
                self.ph_screen()
        else:
            print(self.current_screen)

    def sw_ok_callback(self):
        if self.current_screen == SCREEN.MENU:
            if self.m_indx == 1:
                self.boot_screen()
            elif self.m_indx == 2:
                self.hv_screen()
            elif self.m_indx == 3:
                self.filter_screen()
            elif self.m_indx == 4:
                self.sp_screen()
        elif self.current_screen == SCREEN.BOOT:
            self.menu_screen()
        elif self.current_screen == SCREEN.FILTER:
            if self.f_indx == 1:
                self.ph_screen()
            elif self.f_indx == 2:
                self.hp_screen()
            elif self.f_indx == 3:
                self.de_screen()
            elif self.f_indx == 4:
                self.non_screen()
        elif self.current_screen == SCREEN.HV:
            self.ok_flag = True
            if self.snd_ctrl.get_mute_status(self.snd_ctrl.hv_ctrl) != self.hv_en:
                self.snd_ctrl.change_mute_status(self.snd_ctrl.hv_ctrl)
            self.menu_screen()
        elif self.current_screen == SCREEN.SP:
            self.ok_flag = True
            filter_cur = self.snd_ctrl.getFilterStatus()
            if filter_cur != self.fil_sp:
                self.snd_ctrl.changeFilterStatus()
            self.menu_screen()
        elif self.current_screen == SCREEN.HP:
            self.ok_flag = True
            if self.snd_ctrl.get_mute_status(self.snd_ctrl.hp_ctrl) != self.hp_fil:
                self.snd_ctrl.change_mute_status(self.snd_ctrl.hp_ctrl)
            self.filter_screen()
        elif self.current_screen == SCREEN.DE:
            self.ok_flag = True
            if self.snd_ctrl.get_mute_status(self.snd_ctrl.de_ctrl) != self.de_emp:
                self.snd_ctrl.change_mute_status(self.snd_ctrl.de_ctrl)
            self.filter_screen()
        elif self.current_screen == SCREEN.NON:
            self.ok_flag = True
            if self.snd_ctrl.get_mute_status(self.snd_ctrl.non_ctrl) != self.non_os:
                self.snd_ctrl.change_mute_status(self.snd_ctrl.non_ctrl)
            self.filter_screen()
        elif self.current_screen == SCREEN.PH:
            self.ok_flag = True
            if self.snd_ctrl.get_mute_status(self.snd_ctrl.ph_ctrl) != self.ph_comp:
                self.snd_ctrl.change_mute_status(self.snd_ctrl.ph_ctrl)
            self.filter_screen()

    def sw_up_callback(self):
        if self.current_screen == SCREEN.MENU:
            if self.m_indx > 1:
                self.m_indx -= 1
            self.menu_screen()
        elif self.current_screen == SCREEN.FILTER:
            if self.f_indx > 1:
                self.f_indx -= 1
            self.filter_screen()

    def sw_down_callback(self):
        if self.current_screen == SCREEN.MENU:
            self.m_indx += 1
            if self.m_indx > 4:
                self.m_indx = 1
            self.menu_screen()
        elif self.current_screen == SCREEN.FILTER:
            self.f_indx += 1
            if self.f_indx > 4:
                self.f_indx = 1
            self.filter_screen()
        elif self.current_screen == SCREEN.HV:
            if self.ok_flag:
                self.ok_flag = False
            self.hv_screen()
        elif self.current_screen == SCREEN.SP:
            if self.ok_flag:
                self.ok_flag = False
            self.sp_screen()
        elif self.current_screen == SCREEN.HP:
            if self.ok_flag:
                self.ok_flag = False
            self.hp_screen()
        elif self.current_screen == SCREEN.DE:
            if self.ok_flag:
                self.ok_flag = False
            self.de_screen()
        elif self.current_screen == SCREEN.NON:
            if self.ok_flag:
                self.ok_flag = False
            self.non_screen()
        elif self.current_screen == SCREEN.PH:
            if self.ok_flag:
                self.ok_flag = False
            self.ph_screen()

    def sw_right_callback(self):
        if self.current_screen == SCREEN.MAIN or self.current_screen == SCREEN.BOOT:
            self.menu_screen()
        elif self.current_screen == SCREEN.MENU:
            self.volume_screen()
        elif self.current_screen == SCREEN.HV:
            if self.hv_en:
                self.hv_en = False
            self.hv_screen()
        elif self.current_screen == SCREEN.SP:
            if self.fil_sp:
                self.fil_sp = False
            self.sp_screen()
        elif self.current_screen == SCREEN.HP:
            if self.hp_fil:
                self.hp_fil = False
            self.hp_screen()
        elif self.current_screen == SCREEN.DE:
            if self.de_emp:
                self.de_emp = False
            self.de_screen()
        elif self.current_screen == SCREEN.NON:
            if self.non_os:
                self.non_os = False
            self.non_screen()
        elif self.current_screen == SCREEN.PH:
            if self.ph_comp:
                self.ph_comp = False
            self.ph_screen()

    def button_callback(self, btn: Button):
        self.led_off_counter = 0
        pin_nr = SW_PIN(btn.pin.number)
        if pin_nr == SW_PIN.DOWN:
            self.sw_down_callback()
        elif pin_nr == SW_PIN.UP:
            self.sw_up_callback()
        elif pin_nr == SW_PIN.OK:
            self.sw_ok_callback()
        elif pin_nr == SW_PIN.LEFT:
            self.sw_left_callback()
        elif pin_nr == SW_PIN.RIGHT:
            self.sw_right_callback()


def main():
    sound_ctrl = SOUND_CTRL()
    lcd = OLED(sound_ctrl.card_num, sound_ctrl)
    lcd.boot_screen()

    def cleanup(*args):
        lcd.oled.powerDown()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGHUP, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        # connect to MPD
        mpd_client = PersistentMPDClient(host="localhost", port=6600)
        mpd_client.timeout = 3
        mpd_client.idletimeout = 3
    except Exception as e:
        print(f"Where were error during MPD connection: {e}")

    def remote_callback(ir_dev: InputDevice):
        PRESS_HOLD_EVENTS = [1, 2]
        curr_vol = sound_ctrl.ma_ctrl.get_volume()
        for event in ir_dev.read_loop():
            if event.type == ecodes.EV_KEY and event.value in PRESS_HOLD_EVENTS:
                if event.code == ecodes.KEY_RIGHT:
                    try:
                        mpd_client.next()
                    except Exception:
                        pass
                elif event.code == ecodes.KEY_LEFT:
                    try:
                        mpd_client.previous()
                    except Exception:
                        pass
                elif event.code == ecodes.KEY_MUTE:
                    sound_ctrl.change_mute_status(sound_ctrl.ma_ctrl)
                    sound_ctrl.change_mute_status(sound_ctrl.dig_ctrl)
                    lcd.mute_line()
                elif event.code == ecodes.KEY_PLAY:
                    try:
                        mpd_client.pause()
                    except Exception:
                        pass
                elif event.code == ecodes.KEY_OK:
                    pass
                elif event.code == ecodes.KEY_VOLUMEUP:
                    if curr_vol < 200:
                        new_vol = curr_vol + 2
                    else:
                        new_vol = curr_vol + 1
                    new_vol = min(new_vol, 255)
                    curr_vol = new_vol
                    sound_ctrl.dig_ctrl.set_volume_all(new_vol)
                    sound_ctrl.ma_ctrl.set_volume_all(new_vol)
                    lcd.volume_line(new_vol)
                elif event.code == ecodes.KEY_VOLUMEDOWN:
                    if curr_vol < 200:
                        new_vol = curr_vol - 2
                    else:
                        new_vol = curr_vol - 1
                    new_vol = max(
                        new_vol,
                        0,
                    )
                    curr_vol = new_vol
                    sound_ctrl.dig_ctrl.set_volume_all(new_vol)
                    sound_ctrl.ma_ctrl.set_volume_all(new_vol)
                    lcd.volume_line(new_vol)
                else:
                    pass
                lcd.led_off_counter = 0

    time.sleep(5)

    # setup IR receiver
    devices = [InputDevice(path) for path in list_devices()]
    ir_device: InputDevice
    # find IR setuped via GPIO
    for device in devices:
        if device.name == "gpio_ir_recv":
            ir_device = InputDevice(device.path)
            break
    else:
        ir_device = None
    if ir_device:
        rem_control_thread = threading.Thread(
            name="ir_control",
            target=remote_callback,
            kwargs={"ir_dev": ir_device},
            daemon=True,
        )
        rem_control_thread.start()
    else:
        print("WARNING: Did not find any ir device with name gpio_ir_recv")

    lcd.volume_screen()

    # update hw info line on screen 0
    s = sched.scheduler(time.time, time.sleep)

    def hw_updater(sc):
        lcd.hw_line()
        s.enter(3, 1, hw_updater, (sc,))

    s.enter(3, 1, hw_updater, (s,))
    hw_up_thread = threading.Thread(name="hw_updater", target=s.run, daemon=True)
    hw_up_thread.start()

    btn_left = Button(pin=SW_PIN.LEFT.value, bounce_time=0.05)
    btn_left.when_pressed = lcd.button_callback
    btn_right = Button(pin=SW_PIN.RIGHT.value, bounce_time=0.05)
    btn_right.when_pressed = lcd.button_callback
    btn_up = Button(pin=SW_PIN.UP.value, bounce_time=0.05)
    btn_up.when_pressed = lcd.button_callback
    btn_down = Button(pin=SW_PIN.DOWN.value, bounce_time=0.05)
    btn_down.when_pressed = lcd.button_callback
    btn_ok = Button(pin=SW_PIN.OK.value, bounce_time=0.05)
    btn_ok.when_pressed = lcd.button_callback

    while True:
        if lcd.led_off_counter >= 50:
            lcd.oled.powerDown()
        elif lcd.led_off_counter == 1:
            lcd.oled.powerUp()
        time.sleep(1)
        lcd.led_off_counter += 1


if __name__ == "__main__":
    main()
