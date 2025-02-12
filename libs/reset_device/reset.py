import RPi.GPIO as GPIO
import os
import time
import subprocess
import reset_lib
import socket
from rpi_lcd import LCD
lcd = LCD()

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

counter = 0
serial_last_four = subprocess.check_output(['cat', '/proc/cpuinfo'])[-5:-1].decode('utf-8')
config_hash = reset_lib.config_file_hash()
ssid_prefix = config_hash['ssid_prefix'] + " "
reboot_required = False

reboot_required = reset_lib.wpa_check_activate(config_hash['wpa_enabled'], config_hash['wpa_key'])

reboot_required = reset_lib.update_ssid(ssid_prefix, serial_last_four)

if reboot_required == True:
    os.system('reboot')

# This is the main logic loop waiting for a button to be pressed on GPIO 18 for 10 seconds.
# If that happens the device will reset to its AP Host mode allowing for reconfiguration on a new network.
while True:
    while GPIO.input(18) == 1:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            line1 = s.getsockname()[0]
        except:
            line1 = 'No Connection to router'
            line1 = '     NO IP      '
        lcd.text(line1, 1)
        lcd.text('   RESET in:'+str((counter-9)*-1), 2)
        time.sleep(1)
        counter = counter + 1

        if counter == 9:
            lcd.text('WiFi connect to ', 1)
            lcd.text(' Crypto Monitor ', 2)
            reset_lib.reset_to_host_mode()

        if GPIO.input(18) == 0:
            counter = 0
            break

    time.sleep(1)
