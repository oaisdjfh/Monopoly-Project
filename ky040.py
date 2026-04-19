from machine import Pin
import micropython
import machine
import time

micropython.alloc_emergency_exception_buf(100)

class KY040_PCF:
    def __init__(self, pcf, pin_clk_gpio, pin_dt_pcf, pin_sw=None):
        self.pcf = pcf
        self.pin_clk = Pin(pin_clk_gpio, Pin.IN, Pin.PULL_UP)  # direct GPIO
        self.pin_dt = pin_dt_pcf  # PCF8574 pin number
        self.pin_sw = pin_sw
        self.position = 0
        self.delta = 0
        self._pending_reads = 0
        self.last_clk = self.pin_clk.value()

        # interrupt on CLK directly, no more PCF8574 INT pin needed
        self.pin_clk.irq(trigger=Pin.IRQ_FALLING, handler=self._isr)

    def _isr(self, pin):
        if self._pending_reads < 10:
            self._pending_reads += 1

    def read(self):
        while self._pending_reads > 0:
            state = machine.disable_irq()
            self._pending_reads -= 1
            machine.enable_irq(state)
            try:
                # CLK already triggered via hardware interrupt
                # just read DT from PCF8574 after settle
                time.sleep_us(50)
                dt_val = self.pcf.pin(self.pin_dt)

                if dt_val:
                    self.position += 1
                    self.delta += 1
                else:
                    self.position -= 1
                    self.delta -= 1

            except Exception as e:
                print(f"I2C error: {e}")

        return self.position

    def get_delta(self):
        state = machine.disable_irq()
        d = self.delta
        self.delta = 0
        machine.enable_irq(state)
        return d

    def get_switch(self):
        if self.pin_sw is None:
            return None
        return (self.pcf.port >> self.pin_sw) & 1
