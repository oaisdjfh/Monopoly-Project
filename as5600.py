"""
AS5600 MicroPython Driver
=========================
12-bit magnetic angle position sensor driver for MicroPython.

Wiring (I2C):
    AS5600 SDA  -> MCU SDA
    AS5600 SCL  -> MCU SCL
    AS5600 VCC  -> 3.3V or 5V
    AS5600 GND  -> GND
    AS5600 DIR  -> GND (CW) or 3.3V (CCW)

Usage:
    from machine import I2C, Pin
    from as5600 import AS5600

    i2c = I2C(0, sda=Pin(20), scl=Pin(21), freq=400_000)
    sensor = AS5600(i2c)

    print(sensor.angle)        # degrees (0.0–359.9), relative if origin is set
    print(sensor.absolute_angle)  # always the true absolute angle
    print(sensor.raw_angle)    # raw 12-bit value (0–4095)
    print(sensor.magnitude)    # AGC magnitude (field strength)
    print(sensor.is_magnet_detected())

    # Relative angle usage:
    sensor.set_origin()            # set current position as 0°
    sensor.set_origin(45.0)        # set current position as 45° (offset by -45°)
    sensor.origin = 90.0           # manually set the origin offset in degrees
    print(sensor.angle)            # now returns angle relative to origin (-180 to +180)
    sensor.clear_origin()          # revert .angle to absolute readings
"""

from micropython import const

# I2C address (fixed)
_AS5600_ADDR = const(0x36)

# Register map
_REG_ZMCO      = const(0x00)  # burn count
_REG_ZPOS_H    = const(0x01)  # start position high
_REG_ZPOS_L    = const(0x02)  # start position low
_REG_MPOS_H    = const(0x03)  # stop position high
_REG_MPOS_L    = const(0x04)  # stop position low
_REG_MANG_H    = const(0x05)  # maximum angle high
_REG_MANG_L    = const(0x06)  # maximum angle low
_REG_CONF_H    = const(0x07)  # configuration high
_REG_CONF_L    = const(0x08)  # configuration low
_REG_RAW_ANG_H = const(0x0C)  # raw angle high
_REG_RAW_ANG_L = const(0x0D)  # raw angle low
_REG_ANG_H     = const(0x0E)  # angle high (scaled to ZPOS/MPOS range)
_REG_ANG_L     = const(0x0F)  # angle low
_REG_STATUS    = const(0x0B)  # magnet status
_REG_AGC       = const(0x1A)  # automatic gain control
_REG_MAGNITUDE_H = const(0x1B)
_REG_MAGNITUDE_L = const(0x1C)
_REG_BURN      = const(0xFF)  # burn command register

# Status register bit masks
_STATUS_MH   = const(0x08)   # magnet too strong
_STATUS_ML   = const(0x10)   # magnet too weak
_STATUS_MD   = const(0x20)   # magnet detected

# Configuration register bit fields (CONF_L)
POWER_MODE_NOM   = const(0x00)
POWER_MODE_LPM1  = const(0x01)
POWER_MODE_LPM2  = const(0x02)
POWER_MODE_LPM3  = const(0x03)

HYSTERESIS_OFF  = const(0x00)
HYSTERESIS_1LSB = const(0x04)
HYSTERESIS_2LSB = const(0x08)
HYSTERESIS_3LSB = const(0x0C)

OUTPUT_STAGE_ANALOG_FULL  = const(0x00)
OUTPUT_STAGE_ANALOG_RED   = const(0x10)
OUTPUT_STAGE_DIGITAL_PWM  = const(0x20)

PWM_FREQ_115HZ = const(0x00)
PWM_FREQ_230HZ = const(0x40)
PWM_FREQ_460HZ = const(0x80)
PWM_FREQ_920HZ = const(0xC0)

# Configuration register bit fields (CONF_H)
SLOW_FILTER_16X = const(0x00)
SLOW_FILTER_8X  = const(0x01)
SLOW_FILTER_4X  = const(0x02)
SLOW_FILTER_2X  = const(0x03)

FAST_FILTER_SLOW_ONLY    = const(0x00)
FAST_FILTER_6LSB         = const(0x04)
FAST_FILTER_7LSB         = const(0x08)
FAST_FILTER_9LSB         = const(0x0C)
FAST_FILTER_18LSB        = const(0x10)
FAST_FILTER_21LSB        = const(0x14)
FAST_FILTER_24LSB        = const(0x18)
FAST_FILTER_10LSB        = const(0x1C)

WATCHDOG_OFF = const(0x00)
WATCHDOG_ON  = const(0x20)

# Burn commands
_BURN_ANGLE    = const(0x80)
_BURN_SETTINGS = const(0x40)


class AS5600Error(Exception):
    pass


class AS5600:
    """Driver for the AS5600 12-bit magnetic angle sensor."""

    def __init__(self, i2c, address=_AS5600_ADDR):
        """
        Initialise the AS5600 driver.

        Args:
            i2c:     A configured machine.I2C instance.
            address: I2C address (default 0x36, fixed in hardware).
        """
        self._i2c = i2c
        self._addr = address
        self._buf1 = bytearray(1)
        self._buf2 = bytearray(2)
        self._origin = None  # relative angle origin in degrees, or None for absolute

        # Verify device is present
        if address not in self._i2c.scan():
            raise AS5600Error(f"AS5600 not found at I2C address 0x{address:02X}")

    # ------------------------------------------------------------------
    # Low-level register access
    # ------------------------------------------------------------------

    def _read_u8(self, reg):
        self._buf1[0] = reg
        self._i2c.writeto(self._addr, self._buf1)
        self._i2c.readfrom_into(self._addr, self._buf1)
        return self._buf1[0]

    def _read_u16(self, reg_h):
        self._buf1[0] = reg_h
        self._i2c.writeto(self._addr, self._buf1)
        self._i2c.readfrom_into(self._addr, self._buf2)
        return (self._buf2[0] << 8) | self._buf2[1]

    def _write_u8(self, reg, value):
        self._i2c.writeto(self._addr, bytes([reg, value & 0xFF]))

    def _write_u16(self, reg_h, value):
        self._i2c.writeto(self._addr, bytes([reg_h, (value >> 8) & 0xFF, value & 0xFF]))

    # ------------------------------------------------------------------
    # Angle readings
    # ------------------------------------------------------------------

    @property
    def raw_angle(self):
        """Raw 12-bit angle (0–4095), not affected by ZPOS/MPOS."""
        return self._read_u16(_REG_RAW_ANG_H) & 0x0FFF

    @property
    def absolute_angle(self):
        """
        Absolute angle in degrees (0.0–359.9), always ignoring any origin offset.
        Affected by ZPOS/MPOS start/stop positions if configured in hardware.
        """
        return (self._read_u16(_REG_ANG_H) & 0x0FFF) * 360.0 / 4096.0

    @property
    def angle(self):
        """
        Angle in degrees relative to the set origin (-180.0 to +180.0).
        If no origin has been set, returns the absolute angle (0.0–359.9).

        Use set_origin() to define the zero reference point.
        """
        abs_angle = self.absolute_angle
        if self._origin is None:
            return abs_angle
        # Compute signed relative angle, wrapping to -180..+180
        relative = abs_angle - self._origin
        # Normalise to -180..+180
        relative = (relative + 180.0) % 360.0 - 180.0
        return relative

    @property
    def angle_radians(self):
        """Angle in radians. Relative if origin is set, absolute otherwise."""
        import math
        return self.angle * math.pi / 180.0

    # ------------------------------------------------------------------
    # Relative angle / origin control
    # ------------------------------------------------------------------

    def set_origin(self, reference_degrees=0.0, auto = False):
        """
        Set the current magnet position as the reference (zero) point for
        relative angle readings.

        Args:
            reference_degrees: The value you want the current position to
                               read as. Defaults to 0.0, so the current
                               position becomes 0°. Pass e.g. 45.0 to make
                               the current position report as +45°.

        After calling this, sensor.angle returns a signed value in the range
        -180.0 to +180.0 relative to this origin.

        Example:
            sensor.set_origin()      # current position = 0°
            sensor.set_origin(90.0)  # current position = 90°
        """
        if auto:
            self._origin = 271.0547 - reference_degrees
        else:
            self._origin = self.absolute_angle - reference_degrees

    def clear_origin(self):
        """
        Remove the relative origin. sensor.angle reverts to returning the
        absolute angle (0.0–359.9°).
        """
        self._origin = None

    @property
    def origin(self):
        """
        The stored origin offset in degrees, or None if not set.
        You can assign to this directly to hard-set an offset value.
        """
        return self._origin

    @origin.setter
    def origin(self, degrees):
        """
        Manually set the origin offset in degrees.
        sensor.angle will return (absolute_angle - degrees), wrapped to ±180.

        Set to None to disable relative mode.
        """
        self._origin = degrees

    # ------------------------------------------------------------------
    # Magnet / signal quality
    # ------------------------------------------------------------------

    @property
    def status(self):
        """Raw status register byte."""
        return self._read_u8(_REG_STATUS)

    def is_magnet_detected(self):
        """True if a magnet is present and field strength is acceptable."""
        s = self.status
        return bool(s & _STATUS_MD) and not (s & _STATUS_MH) and not (s & _STATUS_ML)

    def is_magnet_too_strong(self):
        """True if the magnetic field is too strong (magnet too close)."""
        return bool(self.status & _STATUS_MH)

    def is_magnet_too_weak(self):
        """True if the magnetic field is too weak (magnet too far or absent)."""
        return bool(self.status & _STATUS_ML)

    @property
    def agc(self):
        """Automatic Gain Control value (0–255). Lower = stronger field."""
        return self._read_u8(_REG_AGC)

    @property
    def magnitude(self):
        """CORDIC magnitude (0–4095). Indicates field quality."""
        return self._read_u16(_REG_MAGNITUDE_H) & 0x0FFF

    # ------------------------------------------------------------------
    # Position configuration (ZPOS / MPOS / MANG)
    # ------------------------------------------------------------------

    @property
    def start_position(self):
        """Start angle (ZPOS) in raw counts (0–4095)."""
        return self._read_u16(_REG_ZPOS_H) & 0x0FFF

    @start_position.setter
    def start_position(self, value):
        """Set start angle (ZPOS). Value: 0–4095."""
        self._write_u16(_REG_ZPOS_H, value & 0x0FFF)

    @property
    def stop_position(self):
        """Stop angle (MPOS) in raw counts (0–4095)."""
        return self._read_u16(_REG_MPOS_H) & 0x0FFF

    @stop_position.setter
    def stop_position(self, value):
        """Set stop angle (MPOS). Value: 0–4095."""
        self._write_u16(_REG_MPOS_H, value & 0x0FFF)

    @property
    def max_angle(self):
        """Maximum angle (MANG) in raw counts (0–4095)."""
        return self._read_u16(_REG_MANG_H) & 0x0FFF

    @max_angle.setter
    def max_angle(self, value):
        """Set maximum angle (MANG). Value: 0–4095. Overrides MPOS if non-zero."""
        self._write_u16(_REG_MANG_H, value & 0x0FFF)

    def set_start_position_degrees(self, degrees):
        """Set ZPOS from a degree value (0.0–359.9)."""
        self.start_position = int(degrees * 4096.0 / 360.0) & 0x0FFF

    def set_stop_position_degrees(self, degrees):
        """Set MPOS from a degree value (0.0–359.9)."""
        self.stop_position = int(degrees * 4096.0 / 360.0) & 0x0FFF

    def set_max_angle_degrees(self, degrees):
        """Set MANG from a degree value (18.0–360.0). Min is ~18°."""
        self.max_angle = int(degrees * 4096.0 / 360.0) & 0x0FFF

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def configuration(self):
        """Return the full 16-bit CONF register value."""
        return self._read_u16(_REG_CONF_H)

    @configuration.setter
    def configuration(self, value):
        """Write the full 16-bit CONF register."""
        self._write_u16(_REG_CONF_H, value)

    def configure(
        self,
        power_mode=POWER_MODE_NOM,
        hysteresis=HYSTERESIS_OFF,
        output_stage=OUTPUT_STAGE_ANALOG_FULL,
        pwm_freq=PWM_FREQ_115HZ,
        slow_filter=SLOW_FILTER_16X,
        fast_filter=FAST_FILTER_SLOW_ONLY,
        watchdog=WATCHDOG_OFF,
    ):
        """
        Configure the AS5600.

        Args:
            power_mode:   POWER_MODE_NOM, LPM1, LPM2, LPM3
            hysteresis:   HYSTERESIS_OFF, 1LSB, 2LSB, 3LSB
            output_stage: OUTPUT_STAGE_ANALOG_FULL, ANALOG_RED, DIGITAL_PWM
            pwm_freq:     PWM_FREQ_115HZ, 230HZ, 460HZ, 920HZ
            slow_filter:  SLOW_FILTER_16X, 8X, 4X, 2X
            fast_filter:  FAST_FILTER_SLOW_ONLY, 6LSB … 10LSB
            watchdog:     WATCHDOG_OFF, WATCHDOG_ON
        """
        conf_l = power_mode | hysteresis | output_stage | pwm_freq
        conf_h = slow_filter | fast_filter | watchdog
        self._write_u8(_REG_CONF_H, conf_h)
        self._write_u8(_REG_CONF_L, conf_l)

    # ------------------------------------------------------------------
    # Burn commands (one-time, irreversible OTP programming)
    # ------------------------------------------------------------------

    @property
    def burn_count(self):
        """Number of times ZPOS/MPOS have been permanently burned (max 3)."""
        return self._read_u8(_REG_ZMCO)

    def burn_angle(self):
        """
        Permanently burn ZPOS and MPOS into OTP memory.
        WARNING: Irreversible. Maximum 3 times. Requires magnet to be present.
        """
        if not self.is_magnet_detected():
            raise AS5600Error("Magnet not detected; cannot burn angle settings.")
        if self.burn_count >= 3:
            raise AS5600Error("Maximum burn count (3) reached.")
        self._write_u8(_REG_BURN, _BURN_ANGLE)

    def burn_settings(self):
        """
        Permanently burn MANG and CONF into OTP memory.
        WARNING: Irreversible. Can only be done once.
        """
        self._write_u8(_REG_BURN, _BURN_SETTINGS)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def __repr__(self):
        try:
            deg = self.angle
            mag = "OK" if self.is_magnet_detected() else "WEAK/STRONG/ABSENT"
            origin_str = f" origin={self._origin:.2f}°" if self._origin is not None else ""
            return f"<AS5600 angle={deg:.2f}°{origin_str} magnet={mag}>"
        except Exception as e:
            return f"<AS5600 error={e}>"