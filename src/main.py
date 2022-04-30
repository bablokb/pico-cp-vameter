# ----------------------------------------------------------------------------
# main.py: driver program vor VA-meter
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/circuitpython-vameter
#
# ----------------------------------------------------------------------------

import board
import busio
import displayio
import time

import adafruit_displayio_ssd1306          # I2C-OLED display
from adafruit_st7735r import ST7735R       # SPI-TFT  display

from ReadyState  import ReadyState
from ConfigState import ConfigState
from ActiveState import ActiveState

#from FakeDataProvider import DataProvider
from INA219DataProvider import DataProvider
from Touchpad import KeyEventProvider

# --- constants   ------------------------------------------------------------

DEF_INTERVAL   = 100    # sampling-interval:       100ms
DEF_OVERSAMPLE = 1      # oversampling:            1X
DEF_DURATION   = 0      # measurement-duration:    0s     (i.e. not limited)
DEF_UPDATE     = 1000   # display update-interval: 1000ms
DEF_PLOTS      = True   # create plots

BORDER = 1

# for the I2C-display
OLED_ADDR   = 0x3C
OLED_WIDTH  = 128
OLED_HEIGHT = 64
if board.board_id == 'raspberry_pi_pico':
  PIN_SDA = board.GP2
  PIN_SCL = board.GP3
elif hasattr(board,'SDA'):
  PIN_SDA = board.SDA
  PIN_SCL = board.SCL

# for the SPI-display
TFT_WIDTH  = 160
TFT_HEIGHT = 128
TFT_ROTATE = 270
TFT_BGR    = True

PIN_CS  = board.GP9
PIN_DC  = board.GP10
PIN_RST = board.GP11

if board.board_id == 'raspberry_pi_pico':
  PIN_CLK = board.GP14
  PIN_RX  = board.GP16    # unused
  PIN_TX  = board.GP15
elif hasattr(board,'MOSI'):
  PIN_CLK = board.CLK
  PIN_RX  = board.MISO    # unused
  PIN_TX  = board.MOSI

# --- ValueHolder class   ----------------------------------------------------

class ValueHolder:
  pass

# --- application class   ----------------------------------------------------

class VAMeter:
  """ application class """

  # --- constructor   --------------------------------------------------------

  def __init__(self):
    """ constructor """

    if not hasattr(board,'DISPLAY'):
      displayio.release_displays()

    i2c = busio.I2C(sda=PIN_SDA,scl=PIN_SCL)

    self.display = self._get_display(i2c)
    if self.display:
      self.display.auto_refresh = False
    self.border  = BORDER

    self.settings = ValueHolder()
    self.settings.interval   = DEF_INTERVAL
    self.settings.oversample = DEF_OVERSAMPLE
    self.settings.duration   = DEF_DURATION
    self.settings.update     = DEF_UPDATE
    self.settings.plots      = DEF_PLOTS

    self.data_provider  = DataProvider(i2c,self.settings)
    self.results        = ValueHolder()
    self.results.values = [[0,0,0] for i in range(self.data_provider.get_dim())]
    self.results.time   = 0

    try:
      self.key_events = KeyEventProvider(i2c,self.settings)
    except:
      self.key_events = None

    self._ready  = ReadyState(self)
    self._active = ActiveState(self)
    self._config = ConfigState(self)

  # --- initialize display   -------------------------------------------------

  def _get_display(self,i2c):
    """ initialize hardware """

    if hasattr(board,'DISPLAY') and board.DISPLAY:
      return board.DISPLAY
    else:
      # try OLED display first
      try:
        display_bus = displayio.I2CDisplay(i2c, device_address=OLED_ADDR)
        return adafruit_displayio_ssd1306.SSD1306(display_bus,
                                                  width=OLED_WIDTH,
                                                  height=OLED_HEIGHT)
      except:
        pass
      # then try SPI-display
      try:
        spi = busio.SPI(clock=PIN_CLK,MOSI=PIN_TX)       #, MISO=PIN_RX)
        bus = displayio.FourWire(spi,command=PIN_DC,chip_select=PIN_CS,
                                 reset=PIN_RST)
        return ST7735R(bus,width=TFT_WIDTH,height=TFT_HEIGHT,
                       rotation=TFT_ROTATE,bgr=TFT_BGR)
      except:
        raise
        return None

  # --- main loop   ----------------------------------------------------------

  def run(self):
    """ main loop """

    while True:
      next_state = self._ready.run(self._active,self._config)
      if next_state is None:
        break
      next_state.run()
      while not self.key_events:
        # no keypad, start endless sleeping-loop to prevent restart of measurement
        time.sleep(1)

# --- main loop   ------------------------------------------------------------

app = VAMeter()
app.run()

