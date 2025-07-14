__author__ = "tomaxsas"

import os
from setuptools import setup, find_packages

try:
    VERSION = os.environ["VERSION"]
except KeyError:
    VERSION = "0.1.3"

BUILD_NUMBER = "1"
try:
    BUILD_NUMBER = os.environ["BUILD_NUMBER"]
except KeyError:
    pass


config = {
    "name": "allo-boss2",
    "description": "Updated Allo Boss2 OLED and remote control",
    "author": "tomaxsas",
    "author_email": "tomaxsas@gmail.com",
    "version": VERSION,
    "license": "GPL v3.0",
    "entry_points": {"console_scripts": ["allo_boss2=allo_boss2.boss2_oled:main"]},
    "packages": ["allo_boss2", "allo_boss2.Hardware", "allo_boss2.Hardware.SH1106"],
    "data_files": [
        ("/etc/rc_keymaps/", ["allo_boss2_remote.toml"]),
    ],
}

setup(**config)
