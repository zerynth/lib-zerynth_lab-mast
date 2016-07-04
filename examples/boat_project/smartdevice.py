
# import the wifi interface
from wireless import wifi

from zerynth_lab.mast.stm import spwf01 as wifi_driver
from zerynth_lab.mast.zerynth import zstack


uid = None
dev = None
dev_methods = None
_inited =  False

def init(u, m):
    global uid, dev_methods, _inited
    uid = u
    dev_methods = m
    _inited =  True
    
def connect_and_login():
    global dev
    if not _inited:
        raise Exception
    try:
        wifi_driver.init(D24, SERIAL2, baud=9600)
    except Exception as e:
        print(e)

    print("Establishing Link...")
    try:
        wifi.link("Zerynth",wifi.WIFI_WPA2,"zerynthwifi")
    except Exception as e:
        print("ooops, something wrong while linking :(", e)

    print("connected")
    ip = wifi.gethostbyname("mast.zerynth.com")

    try:
        dev = zstack.Device(uid,ip,8080,dev_methods)
        dev.start()
    except Exception as e:
        print(e)
    print("LOGGED!",dev.uid)
    
def send(pkt):
    dev.send(pkt)