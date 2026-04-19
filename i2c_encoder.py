import time

class AdafruitEncoder:
    SEESAW_ADDR  = 0x36
    ENC_BASE     = 0x11
    ENC_POSITION = 0x30
    ENC_DELTA    = 0x40
    GPIO_BASE    = 0x01
    GPIO_BULK    = 0x04
    GPIO_DIRCLR  = 0x03
    GPIO_PULLENSET = 0x0B
    BTN_PIN      = 24

    def __init__(self, i2c):
        self.i2c = i2c

        # software reset
        self._write(0x00, 0x7F, b'\xFF')
        time.sleep_ms(500)

        # enable encoder 0
        self._write(self.ENC_BASE, 0x01, b'\x01')
        time.sleep_ms(10)

        # set button pin as input
        mask = (1 << self.BTN_PIN).to_bytes(4, 'big')
        self._write(self.GPIO_BASE, self.GPIO_DIRCLR, mask)
        time.sleep_ms(10)

        # enable pullup on button pin
        self._write(self.GPIO_BASE, self.GPIO_PULLENSET, mask)
        time.sleep_ms(10)

    def _write(self, module, reg, data=b''):
        self.i2c.writeto(self.SEESAW_ADDR, bytes([module, reg]) + data)
        time.sleep_us(100)

    def _read(self, module, reg, nbytes):
        self.i2c.writeto(self.SEESAW_ADDR, bytes([module, reg]))
        time.sleep_us(1000)
        return self.i2c.readfrom(self.SEESAW_ADDR, nbytes)

    def get_delta(self):
        data = self._read(self.ENC_BASE, self.ENC_DELTA, 4)
        val = int.from_bytes(data, 'big')
        if val & 0x80000000:
            val -= 0x100000000

        # Filter corrupt reads (partial byte transfers), but NOT -1
        if val in (-65536, -16777216):
            return 0

        # Optional: clamp to a sane range to catch other garbage values
        if abs(val) > 100:
            return 0

        return val

    def get_switch(self):
        data = self._read(self.GPIO_BASE, self.GPIO_BULK, 4)
        val = int.from_bytes(data, 'big')
        return 0 if (val & (1 << self.BTN_PIN)) == 0 else 1