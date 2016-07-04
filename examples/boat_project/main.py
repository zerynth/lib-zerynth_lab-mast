################################################################################
# MAST Boat
#
# Created: 2016-06-28 10:20:33.507868
#
################################################################################

import streams
import socket
from smartsensors import analogSensors
from servo import servo

import motor
import smartdevice
import onetemp

def normalizeAirQuality(val, obj):
    return 100*(val/4096)


def move_rudder(cmd):
    print("move rudder.")
    if cmd == "up":
        print("centering")
        rudder.moveToDegree(90)
    elif cmd == "down":
        pass
    elif cmd == "right":
        print("right")
        rudder.moveToDegree(0)
    elif cmd == "left":
        print("left")
        rudder.moveToDegree(180)

def move_dc(cmd):
    print("move dc.")
    if cmd == "up":
        motor.go()
    elif cmd == "down":
        motor.stop()
    elif cmd == "right":
        pass
    elif cmd == "left":
        pass

def set_mode(*args):
    global mode
    mode = int(args[0])
    print("[INFO] entering mode :", mode)

def exe_command(*args):
    print("[INFO] exe cmd in mode: ", mode)
    if mode == 0:
        move_rudder(args[0])
    elif mode == 1:
        move_dc(args[0])


streams.serial()

smartdevice.init("test", {"move":exe_command,"action":set_mode})
smartdevice.connect_and_login()

mode = 0

temperature_sensor = onetemp.get_temp_sensor(I2C1)

rudder = servo.Servo(D6.PWM)
rudder.attach()

motor.init(D8.PWM)

airquality_sensor = analogSensors.AnalogSensor(A2)
airquality_sensor.setNormFunc(normalizeAirQuality)


while True:
    sleep(1000)
    try:
        print(".")
        temp = temperature_sensor.read()
        air  = airquality_sensor.getNormalized()
        smartdevice.send({"cmd":"NTFY","payload":{
                    "type":"Boat",
                    "id":smartdevice.uid,
                    "sensors":[
                        {"name":"temp","value": temp},
                        {"name":"air","value": air}
                     ]
                }})
    except Exception as e:
        print(e)
