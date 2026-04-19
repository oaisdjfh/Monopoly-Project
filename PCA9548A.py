"""
MicroPython Driver for PCA9548A I2C Multiplexer
================================================
The PCA9548A is an 8-channel I2C multiplexer that allows multiple I2C devices
with the same address to coexist on the same bus, and buffers/re-drives signals
for each channel independently.

Default I2C address: 0x70 (A0=A1=A2=GND)
Address range: 0x70 - 0x77 (set via A0, A1, A2 pins)

Usage Example:
    from machine import SoftI2C, Pin
    from pca9548a import PCA9548A

    i2c = SoftI2C(scl=Pin(X), sda=Pin(Y), freq=400000)
    mux = PCA9548A(i2c)

    # Enable channel 0 and talk to a device on it
    with mux.channel(0):
        devices = i2c.scan()
        print(devices)

    # Or manually select channels
    mux.select(0)
    # ... talk to device on channel 0 ...
    mux.select(1)
    # ... talk to device on channel 1 ...
    mux.close()  # disable all channels when done
"""


class PCA9548A:
    """
    Driver for PCA9548A 8-channel I2C multiplexer.

    Parameters
    ----------
    i2c   : machine.I2C or machine.SoftI2C instance
    addr  : I2C address of the PCA9548A (default 0x70)
    """

    def __init__(self, i2c, addr=0x70):
        self.i2c  = i2c
        self.addr = addr
        self._current = None
        self.close()  # start with all channels disabled

    # ── Core channel control ──────────────────────────────────────────────────

    def select(self, channel):
        """
        Enable a single channel (0-7), disabling all others.

        Parameters
        ----------
        channel : int, 0-7
        """
        if not 0 <= channel <= 7:
            raise ValueError("channel must be 0-7")
        self._current = channel
        self.i2c.writeto(self.addr, bytes([1 << channel]))

    def select_multi(self, channels):
        """
        Enable multiple channels simultaneously.
        Useful when you need to broadcast to several devices at once.

        Parameters
        ----------
        channels : list or tuple of ints, each 0-7
        """
        mask = 0
        for ch in channels:
            if not 0 <= ch <= 7:
                raise ValueError(f"channel {ch} must be 0-7")
            mask |= (1 << ch)
        self._current = None  # multiple channels active
        self.i2c.writeto(self.addr, bytes([mask]))

    def close(self):
        """Disable all channels."""
        self._current = None
        self.i2c.writeto(self.addr, bytes([0x00]))

    # ── Context manager support ───────────────────────────────────────────────

    def channel(self, ch):
        """
        Context manager for clean channel selection and auto-close.

        Usage:
            with mux.channel(0):
                # channel 0 is active here
                i2c.writeto(device_addr, data)
            # all channels disabled after the with block
        """
        return _ChannelContext(self, ch)

    # ── Utility ───────────────────────────────────────────────────────────────

    def scan(self, channel):
        """
        Scan for I2C devices on a specific channel.
        Returns a list of addresses found.

        Parameters
        ----------
        channel : int, 0-7
        """
        self.select(channel)
        devices = self.i2c.scan()
        # Filter out the PCA9548A's own address
        devices = [d for d in devices if d != self.addr]
        self.close()
        return devices

    def scan_all(self):
        """
        Scan all 8 channels and return a dict mapping
        channel number to list of device addresses found.

        Usage:
            results = mux.scan_all()
            for ch, devices in results.items():
                print(f"Channel {ch}: {[hex(d) for d in devices]}")
        """
        results = {}
        for ch in range(8):
            found = self.scan(ch)
            if found:
                results[ch] = found
        self.close()
        return results

    @property
    def current_channel(self):
        """Returns the currently active channel, or None if all disabled."""
        return self._current

    def __repr__(self):
        return f"PCA9548A(addr=0x{self.addr:02X}, channel={self._current})"


class _ChannelContext:
    """Internal context manager returned by PCA9548A.channel()"""

    def __init__(self, mux, ch):
        self._mux = mux
        self._ch  = ch

    def __enter__(self):
        self._mux.select(self._ch)
        return self._mux

    def __exit__(self, *args):
        self._mux.close()