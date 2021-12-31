#!/usr/bin/python3
"""IRModuleExample1, program to practice using the IRModule

Created July 30, 2020"""

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

import alsaaudio
import gpiozero
import netifaces
from evdev import InputDevice, ecodes, list_devices
from persistent_mpd import PersistentMPDClient

from Hardware.SH1106.SH1106LCD import *

# Use BCM pin numbeirng scheme
sw_left = 14
sw_ok = 15
sw_up = 23
sw_down = 8
sw_right = 24

m_indx = 1
f_indx = 1
fil_sp = 0
de_emp = 0
non_os = 0
ph_comp = 0
hv_en = 0
hp_fil = 0
ok_flag = 0
card_num = 0

# alsa mixers:
de_ctrl: alsaaudio.Mixer
hp_ctrl: alsaaudio.Mixer
ph_ctrl: alsaaudio.Mixer
non_ctrl: alsaaudio.Mixer
hv_ctrl: alsaaudio.Mixer
sp_ctrl: alsaaudio.Mixer
ma_ctrl: alsaaudio.Mixer
dig_csudotrl: alsaaudio.Mixer

# connect to MPD
MPD_CLIENT = PersistentMPDClient()
MPD_CLIENT.timeout = 3
MPD_CLIENT.idletimeout = 3
MPD_CLIENT.connect("localhost", 6600)

filter_cur = 0
filter_mod = 0
led_off_counter = 0


try:
    ETH_IP = netifaces.ifaddresses("eth0")[2][0]["addr"]
except:
    ETH_IP = ""
try:
    WLAN_IP = netifaces.ifaddresses("wlan0")[2][0]["addr"]
except:
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


scr_num = SCREEN.MAIN


class OLED:
    _h_name = f"HOST: {socket.gethostname()}"

    def __init__(self):
        self.oled = SH1106LCD()
        self.t_lock = threading.Lock()
        self.current_screen = SCREEN.MAIN
        self.lcd_active = True
        self.oled.powerUp()
        self.oled.clearScreen()

    def _check_screen(self, scr: SCREEN):
        if self.current_screen != scr:
            self.oled.clearScreen()
        self.current_screen = scr
        global scr_num
        scr_num = scr

    def boot_screen(self):
        self._check_screen(SCREEN.BOOT)
        if self.lcd_active:
            with self.t_lock:
                self.oled.clearScreen()
                self.oled.displayString("BOSS2", 0, 0)
                self.oled.displayStringNumber(ETH_IP, 2, 0)
                self.oled.displayString(self._h_name, 4, 0)
                self.oled.displayStringNumber(WLAN_IP, 6, 0)

    def volume_line(self, volume):
        if self.current_screen == SCREEN.MAIN:
            if volume is None:
                vol_list = ma_ctrl.getvolume()[0]
            else:
                vol_list = volume
            # TODO find a way to clear row without glitches
            with self.t_lock:
                self.oled.displayString("              ", 1, 10)
                self.oled.centerString(vol_list, 1)

    def mute_line(self):
        if self.current_screen == SCREEN.MAIN:
            with self.t_lock:
                if get_mute_status(ma_ctrl) == 0:
                    self.oled.displayString("@", 3, 50)
                else:
                    self.oled.displayString("  ", 3, 50)

    def hw_line(self):
        bit_rate = "closed"
        bit_format = 0
        if self.current_screen == SCREEN.MAIN:
            # if HW found
            if card_num != -1:
                with open(
                    f"/proc/asound/card{card_num}/pcm0p/sub0/hw_params"
                ) as hw_params:
                    for line in hw_params:
                        if line.startswith("format:"):
                            format_val = line.split(":")
                            bit_rate = format_val[1].strip()[1:3]
                        if line.startswith("rate:"):
                            rate_val = line.split(":")
                            bit_format = int(rate_val[1].strip().split()[0])
                with self.t_lock:
                    # TODO find a way to clear line
                    self.oled.displayString(f"S{bit_rate} {bit_format}", 5, 5)

    def volume_screen(self):
        self._check_screen(SCREEN.MAIN)
        self.volume_line(None)
        self.mute_line()
        self.hw_line()

    def menu_screen(self):
        self._check_screen(SCREEN.MENU)
        if m_indx == 1:
            self.oled.displayInvertedString("SYSINFO", 0, 0)
        else:
            self.oled.displayString("SYSINFO", 0, 0)
        if m_indx == 2:
            if hv_en == 0:
                self.oled.displayInvertedString("HV-EN OFF", 2, 0)
            else:
                self.oled.displayInvertedString("HV-EN ON", 2, 0)
        else:
            if hv_en == 0:
                self.oled.displayString("HV-EN OFF", 2, 0)
            else:
                self.oled.displayString("HV-EN ON", 2, 0)
        if m_indx == 3:
            self.oled.displayInvertedString("FILTER", 4, 0)
        else:
            self.oled.displayString("FILTER", 4, 0)
        if m_indx == 4:
            if fil_sp == 1:
                self.oled.displayInvertedString("F-SPEED-FAS", 6, 0)
            else:
                self.oled.displayInvertedString("F-SPEED-SLO", 6, 0)
        else:
            if fil_sp == 1:
                self.oled.displayString("F-SPEED-FAS", 6, 0)
            else:
                self.oled.displayString("F-SPEED-SLO", 6, 0)

    def filter_screen(self):
        self._check_screen(SCREEN.FILTER)
        if f_indx == 1:
            self.oled.displayInvertedString("PHCOMP ", 0, 5)
            self.oled.displayInvertedString("| ", 0, 64)
            if ph_comp == 0:
                self.oled.displayInvertedString("DIS", 0, 80)
            else:
                self.oled.displayInvertedString("EN", 0, 80)
        else:
            self.oled.displayString("PHCOMP ", 0, 5)
            self.oled.displayString("| ", 0, 64)
            if ph_comp == 0:
                self.oled.displayString("DIS", 0, 80)
            else:
                self.oled.displayString("EN", 0, 80)

        if f_indx == 2:
            self.oled.displayInvertedString("HP-FIL ", 2, 5)
            self.oled.displayInvertedString("| ", 2, 64)
            if hp_fil == 0:
                self.oled.displayInvertedString("DIS", 2, 80)
            else:
                self.oled.displayInvertedString("EN", 2, 80)
        else:
            self.oled.displayString("HP-FIL ", 2, 5)
            self.oled.displayString("| ", 2, 64)
            if hp_fil == 0:
                self.oled.displayString("DIS", 2, 80)
            else:
                self.oled.displayString("EN", 2, 80)
        if f_indx == 3:
            self.oled.displayInvertedString("DE-EMP ", 4, 5)
            self.oled.displayInvertedString("| ", 4, 64)
            if de_emp == 0:
                self.oled.displayInvertedString("DIS", 4, 80)
            else:
                self.oled.displayInvertedString("EN", 4, 80)
        else:
            self.oled.displayString("DE-EMP ", 4, 5)
            self.oled.displayString("| ", 4, 64)
            if de_emp == 0:
                self.oled.displayString("DIS", 4, 80)
            else:
                self.oled.displayString("EN", 4, 80)
        if f_indx == 4:
            self.oled.displayInvertedString("NON-OS ", 6, 5)
            self.oled.displayInvertedString("| ", 6, 64)
            if non_os == 0:
                self.oled.displayInvertedString("DIS", 6, 80)
            else:
                self.oled.displayInvertedString("EN", 6, 80)
        else:
            self.oled.displayString("NON-OS ", 6, 5)
            self.oled.displayString("| ", 6, 64)
            if non_os == 0:
                self.oled.displayString("DIS", 6, 80)
            else:
                self.oled.displayString("EN", 6, 80)

    def sp_screen(self):
        self._check_screen(SCREEN.SP)
        self.oled.displayString("FILTER SPEED", 0, 5)
        if fil_sp == 0:
            self.oled.displayString("FAST", 3, 10)
            self.oled.displayInvertedString("SLOW", 3, 80)
        else:
            self.oled.displayInvertedString("FAST", 3, 10)
            self.oled.displayString("SLOW", 3, 80)
        if ok_flag == 1:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def hp_screen(self):
        self._check_screen(SCREEN.HP)
        self.oled.displayString("HP-FILT", 0, 20)
        if hp_fil == 0:
            self.oled.displayString("EN", 3, 10)
            self.oled.displayInvertedString("DIS", 3, 70)
        else:
            self.oled.displayInvertedString("EN", 3, 10)
            self.oled.displayString("DIS", 3, 70)
        if ok_flag == 1:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def de_screen(self):
        self._check_screen(SCREEN.DE)
        self.oled.displayString("DE-EMPH", 0, 20)
        if de_emp == 0:
            self.oled.displayString("EN", 3, 10)
            self.oled.displayInvertedString("DIS", 3, 70)
        else:
            self.oled.displayInvertedString("EN", 3, 10)
            self.oled.displayString("DIS", 3, 70)
        if ok_flag == 1:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def non_screen(self):
        self._check_screen(SCREEN.NON)
        self.oled.displayString("NON-OSAMP", 0, 20)
        if non_os == 0:
            self.oled.displayString("EN", 3, 10)
            self.oled.displayInvertedString("DIS", 3, 70)
        else:
            self.oled.displayInvertedString("EN", 3, 10)
            self.oled.displayString("DIS", 3, 70)
        if ok_flag == 1:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def ph_screen(self):
        self._check_screen(SCREEN.PH)
        self.oled.displayString("PHA-COMP", 0, 20)
        if ph_comp == 0:
            self.oled.displayString("EN", 3, 10)
            self.oled.displayInvertedString("DIS", 3, 70)
        else:
            self.oled.displayInvertedString("EN", 3, 10)
            self.oled.displayString("DIS", 3, 70)
        if ok_flag == 1:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)

    def hv_screen(self):
        self._check_screen(SCREEN.HV)
        self.oled.displayString("HV ENABLE", 0, 20)
        if hv_en == 0:
            self.oled.displayString("ON", 3, 20)
            self.oled.displayInvertedString("OFF", 3, 70)
        else:
            self.oled.displayInvertedString("ON", 3, 20)
            self.oled.displayString("OFF", 3, 70)
        if ok_flag == 1:
            self.oled.displayInvertedString("OK", 6, 50)
        else:
            self.oled.displayString("OK", 6, 50)


lcd = OLED()


def change_mute_status(mix: alsaaudio.Mixer):
    mute_status = mix.getmute()[0]
    mute_flipped = 1 - mute_status
    mix.setmute(mute_flipped)


def get_mute_status(mix: alsaaudio.Mixer):
    mute_status = mix.getmute()[0]
    mute_flipped = 1 - mute_status
    # originally this lib used 0 for muted and 1 for not muted
    # however alsalib uses 0 for not muted and for muted
    return mute_flipped


def getCardNumber():
    out = subprocess.Popen(
        ["aplay", "-l"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    stdout, _ = out.communicate()
    card_number = None
    line_str = stdout.decode().split("\n")
    for line in line_str:
        if "Boss2" in line:
            word_str = line.split()
            card = word_str[1]
            card_number = card[0]
            break
    return card_number


def getFilterStatus():
    global filter_cur
    cmd = f"amixer -c {card_num} get 'PCM Filter Speed' | grep Item0"
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, _ = proc.communicate()
    word_str = out.decode().split()
    current_status = word_str[1]
    if current_status == "'Slow'":
        filter_cur = 0
    else:
        filter_cur = 1


def setFilterStatus():
    if filter_mod == 0:
        cmd = f"amixer -c {card_num} set 'PCM Filter Speed' Slow"
    else:
        cmd = f"amixer -c {card_num} set 'PCM Filter Speed' Fast"
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    proc.communicate()


def remote_callback(ir_dev: InputDevice):
    global led_off_counter
    PRESS_HOLD_EVENTS = [1, 2]
    for event in ir_dev.read_loop():
        if event.type == ecodes.EV_KEY and event.value in PRESS_HOLD_EVENTS:
            if event.code == ecodes.KEY_RIGHT:
                try:
                    MPD_CLIENT.next()
                except:
                    pass
            elif event.code == ecodes.KEY_LEFT:
                try:
                    MPD_CLIENT.previous()
                except:
                    pass
            elif event.code == ecodes.KEY_MUTE:
                change_mute_status(ma_ctrl)
                change_mute_status(dig_ctrl)
                lcd.mute_line()
            elif event.code == ecodes.KEY_PLAY:
                try:
                    MPD_CLIENT.pause()
                except:
                    pass
            elif event.code == ecodes.KEY_OK:
                pass
            elif event.code == ecodes.KEY_VOLUMEUP:
                new_vol = min(ma_ctrl.getvolume()[0] + 1, 100)
                dig_ctrl.setvolume(new_vol)
                ma_ctrl.setvolume(new_vol)
                lcd.volume_line(new_vol)
            elif event.code == ecodes.KEY_VOLUMEDOWN:
                new_vol = max(ma_ctrl.getvolume()[0] - 1, 0)
                dig_ctrl.setvolume(new_vol)
                ma_ctrl.setvolume(new_vol)
                lcd.volume_line(new_vol)
            else:
                pass
            led_off_counter = 0


def sw_left_callback():
    global hv_en
    global fil_sp
    global hp_fil
    global non_os
    global ph_comp
    global de_emp
    if scr_num == SCREEN.MAIN or scr_num == SCREEN.BOOT or scr_num == SCREEN.MENU:
        lcd.volume_screen()
    elif scr_num == SCREEN.FILTER:
        lcd.menu_screen()
    elif scr_num == SCREEN.HV:
        if hv_en == 0:
            hv_en = 1
            lcd.hv_screen()
    elif scr_num == SCREEN.SP:
        if fil_sp == 0:
            fil_sp = 1
            lcd.sp_screen()
    elif scr_num == SCREEN.HP:
        if hp_fil == 0:
            hp_fil = 1
            lcd.hp_screen()
    elif scr_num == SCREEN.DE:
        if de_emp == 0:
            de_emp = 1
            lcd.de_screen()
    elif scr_num == SCREEN.NON:
        if non_os == 0:
            non_os = 1
            lcd.non_screen()
    elif scr_num == SCREEN.PH:
        if ph_comp == 0:
            ph_comp = 1
            lcd.ph_screen()
    else:
        print(scr_num)


def sw_ok_callback():
    global ok_flag
    global filter_mod
    if scr_num == SCREEN.MENU:
        if m_indx == 1:
            lcd.boot_screen()
        elif m_indx == 2:
            lcd.hv_screen()
        elif m_indx == 3:
            lcd.filter_screen()
        elif m_indx == 4:
            lcd.sp_screen()
    elif scr_num == SCREEN.BOOT:
        lcd.menu_screen()
    elif scr_num == SCREEN.FILTER:
        if f_indx == 1:
            lcd.ph_screen()
        elif f_indx == 2:
            lcd.hp_screen()
        elif f_indx == 3:
            lcd.de_screen()
        elif f_indx == 4:
            lcd.non_screen()
    elif scr_num == SCREEN.HV:
        ok_flag = 0
        if get_mute_status(hv_ctrl) != hv_en:
            change_mute_status(hv_ctrl)
        lcd.menu_screen()
    elif scr_num == SCREEN.SP:
        ok_flag = 0
        getFilterStatus()
        if filter_cur != fil_sp:
            filter_mod = fil_sp
            setFilterStatus()
        lcd.menu_screen()
    elif scr_num == SCREEN.HP:
        ok_flag = 0
        if get_mute_status(hp_ctrl) != hp_fil:
            change_mute_status(hp_ctrl)
        lcd.filter_screen()
    elif scr_num == SCREEN.DE:
        ok_flag = 0
        if get_mute_status(de_ctrl) != de_emp:
            change_mute_status(de_ctrl)
        lcd.filter_screen()
    elif scr_num == SCREEN.NON:
        ok_flag = 0
        if get_mute_status(non_ctrl) != non_os:
            change_mute_status(non_ctrl)
        lcd.filter_screen()
    elif scr_num == SCREEN.PH:
        ok_flag = 0
        if get_mute_status(ph_ctrl) != ph_comp:
            change_mute_status(ph_ctrl)
        lcd.filter_screen()


def sw_up_callback():
    global m_indx
    global f_indx
    if scr_num == SCREEN.MENU:
        if m_indx > 1:
            m_indx -= 1
        lcd.menu_screen()
    elif scr_num == SCREEN.FILTER:
        if f_indx > 1:
            f_indx -= 1
        lcd.filter_screen()


def sw_down_callback():
    global m_indx
    global f_indx
    global ok_flag

    if scr_num == SCREEN.MENU:
        m_indx += 1
        if m_indx > 4:
            m_indx = 1
        lcd.menu_screen()
    elif scr_num == SCREEN.FILTER:
        f_indx += 1
        if f_indx > 4:
            f_indx = 1
        lcd.filter_screen()
    elif scr_num == SCREEN.HV:
        if ok_flag == 0:
            ok_flag = 1
        lcd.hv_screen()
    elif scr_num == SCREEN.SP:
        if ok_flag == 0:
            ok_flag = 1
        lcd.sp_screen()
    elif scr_num == SCREEN.HP:
        if ok_flag == 0:
            ok_flag = 1
        lcd.hp_screen()
    elif scr_num == SCREEN.DE:
        if ok_flag == 0:
            ok_flag = 1
        lcd.de_screen()
    elif scr_num == SCREEN.NON:
        if ok_flag == 0:
            ok_flag = 1
        lcd.non_screen()
    elif scr_num == SCREEN.PH:
        if ok_flag == 0:
            ok_flag = 1
        lcd.ph_screen()


def sw_right_callback():
    global hv_en
    global hp_fil
    global de_emp
    global non_os
    global ph_comp
    global fil_sp
    if scr_num == SCREEN.MAIN or scr_num == SCREEN.BOOT:
        lcd.menu_screen()
    elif scr_num == SCREEN.MENU:
        lcd.volume_screen()
    elif scr_num == SCREEN.HV:
        if hv_en == 1:
            hv_en = 0
        lcd.hv_screen()
    elif scr_num == SCREEN.SP:
        if fil_sp == 1:
            fil_sp = 0
        lcd.sp_screen()
    elif scr_num == SCREEN.HP:
        if hp_fil == 1:
            hp_fil = 0
        lcd.hp_screen()
    elif scr_num == SCREEN.DE:
        if de_emp == 1:
            de_emp = 0
        lcd.de_screen()
    elif scr_num == SCREEN.NON:
        if non_os == 1:
            non_os = 0
        lcd.non_screen()
    elif scr_num == SCREEN.PH:
        if ph_comp == 1:
            ph_comp = 0
        lcd.ph_screen()


def button_callback(btn: gpiozero.Button):
    global led_off_counter
    led_off_counter = 0
    if btn.pin == sw_down:
        sw_down_callback()
    elif btn.pin == sw_up:
        sw_up_callback()
    elif btn.pin == sw_ok:
        sw_ok_callback()
    elif btn.pin == sw_left:
        sw_left_callback()
    elif btn.pin == sw_right:
        sw_right_callback()


def cleanup(*args):
    lcd.oled.powerDown()
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def main():
    global m_indx
    global scr_num
    global f_indx
    global fil_sp
    global hp_fil
    global de_emp
    global ph_comp
    global non_os
    global hv_en
    global ok_flag
    global card_num
    global de_ctrl
    global hp_ctrl
    global hv_ctrl
    global non_ctrl
    global ma_ctrl
    global ph_ctrl
    global sp_ctrl
    global dig_ctrl
    global filter_cur
    global filter_mod
    global led_off_counter
    led_off_counter = 1
    lcd.boot_screen()

    time.sleep(5)
    card_num = getCardNumber()
    if card_num == None:
        print("no boss2 card detected")
        exit(0)

    # setup mixers:
    de_ctrl = alsaaudio.Mixer(control="PCM De-emphasis Filter")
    hp_ctrl = alsaaudio.Mixer(control="PCM High-pass Filter")
    ph_ctrl = alsaaudio.Mixer(control="PCM Phase Compensation")
    non_ctrl = alsaaudio.Mixer(control="PCM Nonoversample Emulate")
    hv_ctrl = alsaaudio.Mixer(control="HV_Enable")
    sp_ctrl = alsaaudio.Mixer(control="PCM Filter Speed")
    ma_ctrl = alsaaudio.Mixer(control="Master")
    dig_ctrl = alsaaudio.Mixer(control="Digital")

    time.sleep(0.04)

    # setup IR receiver
    devices = [InputDevice(path) for path in list_devices()]
    ir_device: InputDevice
    # find IR setuped via GPIO
    for device in devices:
        if device.name == "gpio_ir_recv":
            ir_device = InputDevice(device.path)
            break
    rem_control_thread = threading.Thread(
        name="ir_control", target=remote_callback, kwargs={"ir_dev": ir_device}
    )
    rem_control_thread.start()

    lcd.volume_screen()
    hp_fil = get_mute_status(hp_ctrl)
    hv_en = get_mute_status(hv_ctrl)
    non_os = get_mute_status(non_ctrl)
    ph_comp = get_mute_status(ph_ctrl)
    de_emp = get_mute_status(de_ctrl)
    getFilterStatus()

    # update hw info line on screen 0
    s = sched.scheduler(time.time, time.sleep)

    def hw_updater(sc):
        lcd.hw_line()
        s.enter(5, 1, hw_updater, (sc,))

    s.enter(5, 1, hw_updater, (s,))
    hw_up_thread = threading.Thread(name="hw_updater", target=s.run)
    hw_up_thread.start()

    fil_sp = filter_cur

    btn_left = gpiozero.Button(pin=sw_left, bounce_time=200)
    btn_left.when_pressed = button_callback
    btn_right = gpiozero.Button(pin=sw_right, bounce_time=200)
    btn_right.when_pressed = button_callback
    btn_up = gpiozero.Button(pin=sw_up, bounce_time=200)
    btn_up.when_pressed = button_callback
    btn_down = gpiozero.Button(pin=sw_down, bounce_time=200)
    btn_down.when_pressed = button_callback

    while True:
        if led_off_counter >= 30:
            lcd.oled.powerDown()
        elif led_off_counter == 1:
            lcd.oled.powerUp()
        time.sleep(1)
        led_off_counter += 1


if __name__ == "__main__":
    main()
