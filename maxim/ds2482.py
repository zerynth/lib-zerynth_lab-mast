"""

********
One Wire
********

This module implements the DS2482 functionalities for all models (100,101 and 800).

    """
import i2c

class DS2482(i2c.I2C):
    """
================
DS2482 class
================
.. class:: DS2482(drvname,clock=100000,addr=0x18)
        Creates a DS2482 instance using the MCU I2C circuitry *drvname* (one of I2C0, I2C1, ... check pinmap for details). 
        The created instance is configured and ready to communicate. 
        *clock* is configured by default in slow mode.
        
        DS2482 inherits from i2c.I2C, therefore the method start() must be called to setup the I2C channel
        before using the OneWire bus.
    """       
    def __init__(self,drvname,clock=100000,addr=0x18):
        i2c.I2C.__init__(self,drvname,addr,clock)
        self.ch=0

    def start(self):
        i2c.I2C.start(self)
        _init(self.drvid,self.addr,self.ch)

    def set_channel(self,ch):
        self.ch = ch
        _init(self.drvid,self.addr,self.ch)

    def search_raw(self):
        """
.. method:: search_raw()

    Scan the OneWire bus and collect the 64-bit serial numbers of connected peripherals.

    Return a set containing the serial numbers as byte sequences (bytes type)

        """
        return _search_raw()

    def search(self,sc):
        """
.. method:: search(sc)

    Return a list of items created by calling sc(serial) for each discovered serial number on the OneWire bus.

    Common usage is the following code that creates a list of :class:`OneWireSensor` instances: ::

        from dallas.onewire import sensors

        res = ow.search(sensors.OneWireSensor)
        # ow is a started instance of DS2482 class

        """
        res = self.search_raw(self.ch)
        x = []
        for y in res:
            x.append(sc(y))
        return x

    def ow_reset(self):
        return _owreset()

    def ow_write(self,data):
        for d in data:
            _owwritebyte(d)
    
    def ow_read(self,n=1):
        res = bytearray()
        for x in range(n):
            res.append(_owreadbyte())
        return res
    
    def ow_match_rom(self,rom):
        if self.ow_reset():
            self.ow_write(b'\x55') # match rom command
            self.ow_write(rom)
            return True

           

@c_native("_DS2482_init",["csrc/*"],[])
def _init(drvname,addr,channel):
    """
.. function:: _init(drvname,addr,channel)

    Initialize the DS2482 I2C bridge connected to *drvname* I2C peripheral (I2C0, I2C1, etc..) with address *addr* on channel *channel*.
    Raise exceptions if DS2482 can't be initialized.
    
    """
    pass




@c_native("_ow_search_all",["csrc/*"],[])
def _search_raw():
    """
.. function:: search_raw()

    Scan the OneWire bus and collect the 64-bit serial numbers of connected peripherals.
    
    Return a set containing the serial numbers as byte sequences (bytes type)

    """
    pass


@c_native("_ow_get_funcs",["csrc/*"],[])
def _get_ow_funcs():
    pass


@c_native("_ow_rr",["csrc/*"],[])
def _owreset():
    pass

@c_native("_ow_wb",["csrc/*"],[])
def _owwritebyte(c):
    pass

@c_native("_ow_rb",["csrc/*"],[])
def _owreadbyte():
    pass


def b2s(serial):
    """
.. function:: b2s(serial)

    Convert *serial* given as a byte sequence into the string format. 
    In the string format each byte of serial is converted to hexadecimal and separated by ":"

    """
    x = [hex(y,"") for y in serial]
    return ":".join(x)

def s2b(serial):
    """
.. function:: s2b(serial)

    Convert *serial* given in the string format to a byte sequence.

    """
    flds = serial.split(":")
    x = [int(y,16) for y in flds]
    return bytes(x)




class OneWireSensor():
    """
===================
OneWireSensor class
===================

.. class:: OneWireSensor(serial,owbus)

    Create a OneWireSensor instance with serial set to *serial*. *serial* can be a string in the appropriate format
    or a byte sequence (both bytes or bytearray).
    
    The first byte of the serial identifies the sensor family. If the family is not supported
    UnsupportedError is raised.
    
    The following members are available:
    
        * **serial**: serial number as a byte sequence
        * **typeid**: the family number of the peripheral
    
    If a OneWireSensor instance is converted to string, the result is the serial number in the string format.

    """
    def __init__(self,serial,owbus):
        if type(serial)==PSTRING:
            self.serial=s2b(serial)
        elif type(serial)!=PBYTES and type(serial)!=PBYTEARRAY:
            raise TypeError
        else:
            self.serial=serial

        self.owbus = owbus
        self.typeid = serial[0]

    def read(self):
        """
.. method:: read()

    Return a single reading from the sensor. The result value depends on the sensor family.

    PeripheralError is raised if there is a problem in the OneWire bus.

    InvalidHardwareStatusError is raised if a peripherla on the OneWire bus does not respond (e.g. it is disconnected)

        """
        raise NotImplementedError
        
    def __str__(self):
        return b2s(self.serial)
