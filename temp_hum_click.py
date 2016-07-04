"""
.. module:: TempHumClick

================
Temp & Hum click
================

This module contains the :class:`TempHumClick` carries STs HTS221
temperature and relative humidity sensor. Its highlight is that it
outputs its measurement in a 16-bit resolution and has a high
rH sensitivity of 0.004% (although the accuracy range. In comparison,
HTU21D click, HDC1000 click and SHT1x click all output a 12-14 bit
resolution signal.

**Resources**

* Datasheet:
http://www.st.com/st-web-ui/static/active/en/resource/technical/document/datasheet/DM00116291.pdf

* Product Page: http://www.mikroe.com/click/temp-hum/

* Product Manual:
http://www.mikroe.com/downloads/get/2383/temp_hum_click_user_manual_v100.pdf

    """


import i2c


class TempHumClick():
    """

.. class:: TempHumClick

    Creates an intance of a new TempHumClick.

    :param drvsel: I2C Bus used `( I2C0, I2C0 )`
    :param int_pin: Interrupt pin used for events
    :param address: Slave address, default 0x5f
    :param clk: Clock speed, default 400kHz

    :Example:

.. code-block:: python

    temp_hum = tempnhum_click.TempHumClick( I2C1,D31 )
    temp, hum = temp_hum.get_temp_humidity()

    """
    def __init__(self, drvsel, int_pin, address=0x5F, clk=400000):
        self.port = i2c.I2C(drvsel, address, clk)
        self.H0_T0_OUT   = 0
        self.H1_T0_OUT   = 0
        self.T0_OUT      = 0
        self.T1_OUT      = 0
        self.T0_DegC_cal = 0.0
        self.T1_DegC_cal = 0.0
        self.H0_RH_cal   = 0.0
        self.H1_RH_cal   = 0.0
        self.int_pin     = int_pin

        try:
            self.port.start()
        except PeripheralError as e:
            print(e)

        pinMode(int_pin, INPUT)

        self._write(0x10, 0x1B)
        self._write(0x20, 0x85)
        self._write(0x21, 0x00)
        self._write(0x22, 0x00)
        self._calibrate()

    def _write(self, addr, data):
        buffer = bytearray(1)
        buffer[0] = addr
        buffer.append(data)

        self.port.write(buffer)

    def _read(self, addr, num_bytes):
        return self.port.write_read(addr, num_bytes)

    def _linear(self,x0, y0, x1, y1, mes):
        a = ((y1 - y0) / (x1 - x0))
        b = (-a * x0 + y0)
        cal = (a * mes + b)
        return cal

    def _calibrate(self):
        tmp_data = self._read(0xB0,16)

        H0_rH_x2 = tmp_data[0]
        H1_rH_x2 = tmp_data[1]
        T0_degC_x8 = ((tmp_data[5] & 0x03) << 8) + tmp_data[2]
        T1_degC_x8 = ((tmp_data[5] & 0x0C) << 6) + tmp_data[3]

        self.H0_T0_OUT = (tmp_data[7] << 8) + tmp_data[6]
        self.H1_T0_OUT = (tmp_data[11] << 8) + tmp_data[10]
        self.T0_OUT = (tmp_data[13] << 8) + tmp_data[12]
        self.T1_OUT = (tmp_data[15] << 8) + tmp_data[14]

        # convert negative 2's complement values to native negative value
        if (self.H0_T0_OUT & 0x8000):
            self.H0_T0_OUT = -(0x8000-(0x7fff & self.H0_T0_OUT))
        if (self.H1_T0_OUT & 0x8000):
            self.H1_T0_OUT = -(0x8000-(0x7fff & self.H1_T0_OUT))
        if (self.T0_OUT & 0x8000):
            self.T0_OUT = -(0x8000-(0x7fff & self.T0_OUT))
        if (self.T1_OUT & 0x8000):
            self.T1_OUT = -(0x8000-(0x7fff & self.T1_OUT))

        self.T0_DegC_cal = (T0_degC_x8 / 8)
        self.T1_DegC_cal = (T1_degC_x8 / 8)
        self.H0_RH_cal = (H0_rH_x2 / 2)
        self.H1_RH_cal = H1_rH_x2 / 2

    def get_temp_humidity(self):
        """

.. method:: get_temp_humidity()

        Retrieves both temperature and humidity in one call.

        returns temp, humidity

        """
        MAXTEMP = 120
        MINTEMP = -40
        MAXHUMI = 100
        MINHUMI = 0

        tmp_data = self._read(0xA8, 4)

        hum_raw = (tmp_data[1] << 8) + tmp_data[0]
        temp_raw = (tmp_data[3] << 8) + tmp_data[2]

        if (hum_raw & 0x8000):
            hum_raw = -(0x8000 - (0x7fff & hum_raw))
        if (temp_raw & 0x8000):
            temp_raw = -(0x8000 - (0x7fff & temp_raw))

        temp = self._linear(self.T0_OUT, self.T0_DegC_cal, self.T1_OUT, self.T1_DegC_cal, temp_raw)
        hum  = self._linear(self.H0_T0_OUT, self.H0_RH_cal, self.H1_T0_OUT, self.H1_RH_cal, hum_raw)
        # Constraint for measurement after calibration
        if hum > (MAXHUMI - 1): # | hum ==- 72):
            hum = MAXHUMI
        if hum < MINHUMI:
            hum = MINHUMI
        if temp > (MAXTEMP - 1):
            temp = MAXTEMP
        if temp < MINTEMP:
            temp = MINTEMP
        temp += 22

        return temp, hum 
