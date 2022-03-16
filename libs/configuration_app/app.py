from dataclasses import dataclass
from flask import Flask, render_template, request
import subprocess
import os
import time
from threading import Thread
import fileinput
from rpi_lcd import LCD
from pycoingecko import CoinGeckoAPI
app = Flask(__name__)
app.debug = False
lcd = LCD()
cg = CoinGeckoAPI()
run = False


@app.route('/')
def index():
    lcd.text('    WELCOME!    ', 1)
    lcd.text('CryptoMonitor1.0', 2)
    if not cm.is_alive():
     try:
      cm.start()
     except:
      lcd.text('NETWORK ERROR 1', 1)
      lcd.text('http://10.0.0.1/', 2)

    return render_template('home.html', active='/')


@app.route('/wifi')
def wifi():
    wifi_ap_array = scan_wifi_networks()
    config_hash = config_file_hash()
    lcd.text('    SETTINGS    ', 1)
    lcd.text('Please set WiFi ', 2)
    return render_template('app.html', wifi_ap_array=wifi_ap_array, config_hash=config_hash, active='/wifi')


@app.route('/manual_ssid_entry')
def manual_ssid_entry():
    return render_template('manual_ssid_entry.html', active='/manual_ssid_entry')


@app.route('/coins')
def coins():
    config_hash = config_file_hash()
    return render_template('coins.html', active='/coins', coin1=config_hash['coin1'], coin2=config_hash['coin2'], dec1=config_hash['dec1'], dec2=config_hash['dec2'])


@app.route('/wpa_settings')
def wpa_settings():
    config_hash = config_file_hash()
    return render_template('wpa_settings.html', wpa_enabled=config_hash['wpa_enabled'], wpa_key=config_hash['wpa_key'], active='/wpa_setting')


@app.route('/save_credentials', methods=['GET', 'POST'])
def save_credentials():
    ssid = request.form['ssid']
    wifi_key = request.form['wifi_key']

    lcd.text('  READY!        ', 1)
    lcd.text('Wait for reboot ', 2)
    create_wpa_supplicant(ssid, wifi_key)

    # Call set_ap_client_mode() in a thread otherwise the reboot will prevent
    # the response from getting to the browser
    def sleep_and_start_ap():
        time.sleep(2)
        set_ap_client_mode()
    t = Thread(target=sleep_and_start_ap)
    t.start()

    return render_template('save_credentials.html', ssid=ssid)


@app.route('/coins', methods=['GET', 'POST'])
def save_coins():
    coin1 = request.form['coin1']
    dec1 = request.form['dec1']
    coin2 = request.form['coin2']
    dec2 = request.form['dec2']
    update_coins(coin1, dec1, coin2, dec2)

    return render_template('coins.html', active='/coins', coin1=coin1, dec1=dec1, coin2=coin2, dec2=dec2)


@app.route('/save_wpa_credentials', methods=['GET', 'POST'])
def save_wpa_credentials():
    config_hash = config_file_hash()
    wpa_enabled = request.form.get('wpa_enabled')
    wpa_key = request.form['wpa_key']

    if str(wpa_enabled) == '1':
        update_wpa(1, wpa_key)
    else:
        update_wpa(0, wpa_key)

    def sleep_and_reboot_for_wpa():
        time.sleep(2)
        os.system('reboot')

    t = Thread(target=sleep_and_reboot_for_wpa)
    t.start()

    config_hash = config_file_hash()
    return render_template('save_wpa_credentials.html', wpa_enabled=config_hash['wpa_enabled'], wpa_key=config_hash['wpa_key'])

######## FUNCTIONS ##########

def get_data():
    coin_hash = config_file_hash()
    dec1 = coin_hash['dec1']
    dec2 = coin_hash['dec2']
    try:
        btc = cg.get_coin_by_id(id=coin_hash['coin1'], localization='false',
                                tickers='false', community_data='false', developer_data='false')
        eth = cg.get_coin_by_id(id=coin_hash['coin2'], localization='false',
                                tickers='false', community_data='false', developer_data='false')
        bprice = btc['market_data']['current_price']['usd']
        eprice = eth['market_data']['current_price']['usd']
        bp = btc['market_data']['price_change_percentage_24h']
        ep = eth['market_data']['price_change_percentage_24h']
        if bp > 0:
            l1 = (btc['symbol'].upper()+' +' +
                    str(f'{bp:4.2f}')+str(f' {bprice:5.{dec1}f}'))
        else:
            l1 = (btc['symbol'].upper()+' ' +
                    str(f'{bp:4.2f}')+str(f' {bprice:5.{dec1}f}'))
        if ep > 0:
            l2 = (eth['symbol'].upper()+' +' +
                    str(f'{ep:4.2f}')+str(f' {eprice:5.{dec2}f}'))
        else:
            l2 = (eth['symbol'].upper()+' ' +
                    str(f'{ep:4.2f}')+str(f' {eprice:5.{dec2}f}'))
        data={"l1":l1,"l2":l2}
    except:
        data={"l1":"Something","l2":"went wrong"}
    return data

def start_print():
    while True:
        data=get_data()
        lcd.text(data.l1, 1)
        lcd.text(data.l2, 2)
        print(data.l1+'   '+data.l2)
        time.sleep(10)


def scan_wifi_networks():
    iwlist_raw = subprocess.Popen(['iwlist', 'scan'], stdout=subprocess.PIPE)
    ap_list, err = iwlist_raw.communicate()
    ap_array = []

    for line in ap_list.decode('utf-8').rsplit('\n'):
        if 'ESSID' in line:
            ap_ssid = line[27:-1]
            if ap_ssid != '':
                ap_array.append(ap_ssid)

    return ap_array


def create_wpa_supplicant(ssid, wifi_key):
    temp_conf_file = open('wpa_supplicant.conf.tmp', 'w')

    temp_conf_file.write(
        'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
    temp_conf_file.write('update_config=1\n')
    temp_conf_file.write('\n')
    temp_conf_file.write('network={\n')
    temp_conf_file.write('      ssid="' + ssid + '"\n')

    if wifi_key == '':
        temp_conf_file.write('  key_mgmt=NONE\n')
    else:
        temp_conf_file.write('  psk="' + wifi_key + '"\n')

    temp_conf_file.write('      }')

    temp_conf_file.close

    os.system('mv wpa_supplicant.conf.tmp /etc/wpa_supplicant/wpa_supplicant.conf')


def set_ap_client_mode():
    os.system('rm -f /etc/raspiwifi/host_mode')
    os.system('rm /etc/cron.raspiwifi/aphost_bootstrapper')
    os.system(
        'cp /usr/lib/raspiwifi/reset_device/static_files/apclient_bootstrapper /etc/cron.raspiwifi/')
    os.system('chmod +x /etc/cron.raspiwifi/apclient_bootstrapper')
    os.system('mv /etc/dnsmasq.conf.original /etc/dnsmasq.conf')
    os.system('mv /etc/dhcpcd.conf.original /etc/dhcpcd.conf')
    os.system('reboot')


def update_wpa(wpa_enabled, wpa_key):
    with fileinput.FileInput('/etc/raspiwifi/raspiwifi.conf', inplace=True) as raspiwifi_conf:
        for line in raspiwifi_conf:
            if 'wpa_enabled=' in line:
                line_array = line.split('=')
                line_array[1] = wpa_enabled
                print(line_array[0] + '=' + str(line_array[1]))

            if 'wpa_key=' in line:
                line_array = line.split('=')
                line_array[1] = wpa_key
                print(line_array[0] + '=' + line_array[1])

            if 'wpa_enabled=' not in line and 'wpa_key=' not in line:
                print(line, end='')


def update_coins(coin1, dec1, coin2, dec2):
    with fileinput.FileInput('/etc/raspiwifi/raspiwifi.conf', inplace=True) as raspiwifi_conf:
        for line in raspiwifi_conf:
            if 'coin1=' in line:
                line_array = line.split('=')
                line_array[1] = coin1
                print(line_array[0] + '=' + line_array[1])
            if 'dec1=' in line:
                line_array = line.split('=')
                line_array[1] = dec1
                print(line_array[0] + '=' + line_array[1])

            if 'coin2=' in line:
                line_array = line.split('=')
                line_array[1] = coin2
                print(line_array[0] + '=' + line_array[1])
            if 'dec2=' in line:
                line_array = line.split('=')
                line_array[1] = dec2
                print(line_array[0] + '=' + line_array[1])

            if 'coin1=' not in line and 'dec1=' not in line and 'coin2=' not in line and 'dec2=' not in line:
                print(line, end='')


def config_file_hash():
    config_file = open('/etc/raspiwifi/raspiwifi.conf')
    config_hash = {}

    for line in config_file:
        line_key = line.split("=")[0]
        line_value = line.split("=")[1].rstrip()
        config_hash[line_key] = line_value

    return config_hash


cm = Thread(target=start_print, name='printing')
try:
    lcd.text(' Connetcting... ', 1)
    time.sleep(5)
    cm.start()
except:
    lcd.text(' NETWORK ERROR 2', 1)
    lcd.text('http://10.0.0.1/', 2)

if __name__ == '__main__':
    config_hash = config_file_hash()

    if config_hash['ssl_enabled'] == "1":
        app.run(host='0.0.0.0', port=int(
            config_hash['server_port']), ssl_context='adhoc')
    else:
        app.run(host='0.0.0.0', port=int(config_hash['server_port']))
