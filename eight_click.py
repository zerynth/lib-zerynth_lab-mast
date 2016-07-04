"""
.. module:: Click_8x8

*********
Click 8x8
*********

Used with seven segment displays and 8x8 matrix of LEDs.

    """

import spi



class LedDisplay(spi.Spi):
    """
.. class: LedDisplay(cs, max_devices=1, spidrv=SPI0)

    Constructor takes a chip select pin *cs*, maximum number of devices attached
    *max_devices* and which spi bus *spidrv* the unit is connected to.

    At the moment only 1 device is supported.

    """
    DIGIT0          = 1
    DIGIT1          = 2
    DIGIT2          = 3
    DIGIT3          = 4
    DIGIT4          = 5
    DIGIT5          = 6
    DIGIT6          = 7
    DIGIT7          = 8
    NO_OP           = 0x00
    SHUTDOWN        = 0x0C
    SHUTDOWN_MODE   = 0
    SHUTDOWN_NORMAL = 1
    DECODE_MODE     = 0x09
    INTENSITY       = 0x0A
    SCAN_LIMIT      = 0x0B
    DISPLAY_TEST    = 0x0F

    """
    Segments to be switched on for characters and digits on
    7-Segment Displays
    """
    char_table = bytes((
        0b01111110,0b00110000,0b01101101,0b01111001,0b00110011,0b01011011,0b01011111,0b01110000,
        0b01111111,0b01111011,0b01110111,0b00011111,0b00001101,0b00111101,0b01001111,0b01000111,
        0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,
        0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,
        0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,
        0b00000000,0b00000000,0b00000000,0b00000000,0b10000000,0b00000001,0b10000000,0b00000000,
        0b01111110,0b00110000,0b01101101,0b01111001,0b00110011,0b01011011,0b01011111,0b01110000,
        0b01111111,0b01111011,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,
        0b00000000,0b01110111,0b00011111,0b00001101,0b00111101,0b01001111,0b01000111,0b00000000,
        0b00110111,0b00000000,0b00000000,0b00000000,0b00001110,0b00000000,0b00000000,0b00000000,
        0b01100111,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,
        0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00001000,
        0b00000000,0b01110111,0b00011111,0b00001101,0b00111101,0b01001111,0b01000111,0b00000000,
        0b00110111,0b00000000,0b00000000,0b00000000,0b00001110,0b00000000,0b00010101,0b00011101,
        0b01100111,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,
        0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000
    ,))


    def __init__(self, cs, max_devices=1, spidrv=SPI0):
        spi.Spi.__init__(self, cs, spidrv, clock=1000000)
        self.max_devices = max_devices

        # The array for shifting the data to the devices
        self.spidata = bytearray(16)

        # We keep track of the led-status for all 8 devices in this array
        self.status = bytearray(64)

        for i in self.status:
            self.status[i] = 0x00

        for i in range(self.max_devices):
            self._write( i, self.DISPLAY_TEST, 0)
            # scanlimit is set to max on startup
            self.set_scan_limit(i, 0x07)
            # decode is done in source
            self._write(i, self.DECODE_MODE, 0)
            self.clear_display(i)
            # we go into shutdown-mode on startup
            self.shutdown(i, True)

    # Write value to BUS
    def _write(self, address, opcode, data):
        # Create an array with the data to shift out
        buffer = bytearray(0)
        offset = address * 2
        maxbytes = self.max_devices * 2

        for i in range(maxbytes):
            self.spidata[i] = 0

        # Put our device data into the array
        self.spidata[offset+1] = opcode
        self.spidata[offset] = data

        for i in range(maxbytes, 0, -1):
                buffer.append(self.spidata[i-1])

        self.lock()

        # enable the line
        self.select()

        try:
            self.write(buffer)
        except Exception as e:
            print(e)
        finally:
            self.unselect()
            self.unlock()

    def get_device_count(self):
        """
.. method:: get_device_count()

            Returns the number of devices attached.
        """
        return self.max.devices

    def shutdown(self, dev_num, powerdown):
        """
.. method:: shutdown(dev_num, powerdown)

        *dev_num* is the device id, with 1 device on the bus, the id of the unit is 0.
        *powerdown* is a boolean that is ``True`` or ``False``
        """
        if (dev_num < 0) or (dev_num >= self.max_devices):
            return
        if powerdown:
            self._write(dev_num, self.SHUTDOWN, self.SHUTDOWN_MODE)
        else:
            self._write(dev_num, self.SHUTDOWN, self.SHUTDOWN_NORMAL)

    def set_scan_limit(self, dev_num, limit):
        """
.. method:: set_scan_limit(dev_num, limit)

        Method that is used for seven segment displays that limits the number of digits.

        *dev_num* is the device id, with 1 device on the bus, the id of the unit is 0.
        *limit* is the number of banks values 0 to 7.
        """
        if (dev_num < 0) or (dev_num >= self.max_devices):
            return
        if (limit >= 0) and (limit < 8):
            self._write(dev_num, self.SCAN_LIMIT, limit)

    def set_intensity(self, dev_num, intensity):
        """
.. method:: set_intensity(dev_num, intensity)

        Sets the intensity of the LEDs output.

        *dev_num* is the device id, with 1 device on the bus, the id of the unit is 0.
        *intensity* is the light output intensity values 0 to 15.
        """
        if (dev_num < 0) or (dev_num >= self.max_devices):
            return
        if (intensity >= 0) and (intensity < 16):
            self._write(dev_num, self.INTENSITY, intensity)

    def clear_display(self, dev_num):
        """
.. method:: clear_display(dev_num)

        Clears the display by setting all LEDs to 0.
        """
        if (dev_num < 0) or (dev_num >= self.max_devices):
            return

        offset = dev_num * 8

        for i in range(8):
            self.status[offset+i] = 0
            self._write(dev_num, i + 1, self.status[offset+i])


    def set_led(self, dev_num, row, column, state):
        """
.. method:: set_led(dev_num, row, column, state)

        Allows the control of a single LED. 
        *dev_num* is the device id, with 1 device on the bus, the id of the unit is 0.
        *row* is the row 0 to 7
        *column* is the column 0 to 7
        *state* is ``True`` for ON, and ``False`` for OFF
        """
        if (dev_num < 0) or (dev_num >= self.max_devices):
            return
        if (row < 0) or (row > 7) or (column < 0) or (column > 7):
            return

        offset = dev_num * 8
        val = 0x80 >> column;

        if state:
            self.status[offset + row] = self.status[offset+row] | val
        else:
            val =~ val
            self.status[offset+row] = self.status[offset+row] & val

        self._write( dev_num, row + 1, self.status[offset+row])


    def set_row(self, dev_num, row, value):
        """
.. method:: set_row(dev_num, row, value)

        Controls an entire row.
        *dev_num* is the device id, with 1 device on the bus, the id of the unit is 0.
        *row* to control, values from 0 to 7
        *value* is ``True`` for ON or ``False`` for OFF.
        """
        if (dev_num < 0) or (dev_num >= self.max_devices):
            return
        if (row < 0) or row:
            return

        offset = dev_num * 8
        self.status[offset+row] = value
        self._write(dev_num, row + 1, self.status[offset+row])


    def set_column(self, dev_num, col, value):
        """
.. method:: set_column(dev_num, col, value)

        Controls and entire column.0
        *dev_num* is the device id, with 1 device on the bus, the id of the unit is 0.
        *col* to control, values from 0 to 7
        *value* is ``True`` for ON or ``False`` for OFF.
        """
        val = 0x00

        if (dev_num < 0) or (dev_num >= self.max_devices):
            return
        if (col < 0) or (col > 7):
            return
        for row in range(8):
            val = value >> (7 - row)
            val = val & 0x01
            self.set_led(dev_num, row, col, val)

    def set_digit(self, dev_num, digit, value, dp):
        """
..method:: set_digit(dev_num, digit, value, dp)

        Used with 7 segment displays to set a digit to display on the 7 segments.

        *dev_num* is the device id, with 1 device on the bus, the id of the unit is 0.
        *digit* is the bank from 0 to 7 to display
        *value* is the number value
        *dp* is the decimal point

        """
        if (dev_num < 0) or (dev_num >= self.max_devices):
            return
        if (digit < 0) or (digit > 7) or (value > 15):
            return
        offset = dev_num * 8
        v = self.char_table[value]

        if dp:
            v |= 0x80
        self.status[offset+digit] = v
        self._write(dev_num, digit + 1, v)

    def set_char(self, dev_num, digit, value, on_off):
        """
..method:: set_char(dev_num, digit, value, on_off)

        *dev_num* is the device id, with 1 device on the bus, the id of the unit is 0.
        *digit* bank from 0 to 7
        *value* is the character value.
        *on_off* is ``True`` for ON and ``False`` for OFF
        """
        if (dev_num < 0) or (dev_num >= self.max_devices):
            return
        if (digit < 0) or (digit > 7):
            return
        offset = dev_num * 8
        index = value

        if index > 127:
            #no defined beyond index 127, so we use the space char
            index = 32

        v = self.char_table[index]

        if on_off:
            v |= 0x80
        self.status[offset+digit] = v
        self._write(dev_num, digit+1, v)
