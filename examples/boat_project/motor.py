import pwm

motorpin = None
_inited  = False

def init(pin):
    global motorpin, _inited
    motorpin = D8.PWM
    pinMode(motorpin, OUTPUT)
    pwm.write(motorpin, 1000, 0, MICROS)
    _inited = True

def go():
    if not _inited:
        raise Exception
    pwm.write(motorpin, 1000, 950, MICROS)
    
def stop():
    if not _inited:
        raise Exception    
    pwm.write(motorpin, 1000, 0, MICROS)