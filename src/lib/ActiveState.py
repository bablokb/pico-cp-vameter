# ----------------------------------------------------------------------------
# ActiveState.py: Handle active-state, i.e. display current values
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/circuitpython-vameter
#
# ----------------------------------------------------------------------------

import time
import sys
from View import ValuesView, PlotView
from Data import DataAggregator

class ActiveState:
  """ manage active-state """

  # --- constructor   --------------------------------------------------------

  def __init__(self,app):
    """ constructor """

    self._app      = app
    self._settings = app.settings
    self._logger   = app.logger
    if app.settings.tm_scale == 'ms':
      self._tm_scale = 0.001
    else:
      self._tm_scale = 1
    self._dim      = app.data_provider.get_dim()
    if self._app.display:
      self._views = [ValuesView(app.display,app.border,
                                 app.data_provider.get_units()),
                      ValuesView(app.display,app.border,['s','s'])]  # elapsed
      if self._settings.plots:
        for unit in app.data_provider.get_units():
          self._views.append(PlotView(app.display,app.border,[unit]))

  # --- get data   -----------------------------------------------------------

  def _get_data(self):
    """ get data using oversampling """

    if self._settings.oversample < 2:
      return (time.monotonic(),self._app.data_provider.get_data())

    d_sum = [0 for i in range(self._dim)]
    for o in range(self._settings.oversample):
      data = self._app.data_provider.get_data()
      for i in range(self._dim):
        d_sum[i] += data[i]
    return (time.monotonic(),
            [d_sum[i]/self._settings.oversample for i in range(self._dim)])

  # --- loop during ready-state   --------------------------------------------

  def run(self):
    """ main-loop during active-state """

    self._logger.log_settings()
    m_data = DataAggregator(self._dim)
    c_view = 0
    if self._app.display:
      if self._settings.plots:
        # reset plots and show first ValuesView
        for i in range(self._dim):
          self._views[2+i].reset()
      self._views[0].clear_values()
      self._views[0].show()

    # reset data-provider and wait for first sample
    self._app.data_provider.reset()
    try:
      self._app.data_provider.get_data()
    except:
      print("\n#data-provider timed out")
      return

    if self._settings.duration:
      end_t = time.monotonic() + self._settings.duration
    else:
      end_t = sys.maxsize

    data_t0 = 0                                      # timestamp before last sample
    stop    = False                                  # global stop
    int_t   = self._settings.interval*self._tm_scale # interval time in sec
    start_t = time.monotonic()                       # timestamp of start
    samples = 0                                      # total number of samples

    # sample until manual stop or until end of duration
    while not stop and time.monotonic() < end_t:

      # calc next screen update
      if self._app.display and self._settings.update:
        display_next = time.monotonic() + self._settings.update*self._tm_scale
      else:
        display_next = end_t
      # sample until screen-update is necessary
      while not stop and time.monotonic() < display_next:

        # sleep until next sampling interval starts (int_t minus overhead)
        if data_t0 > 0:
          time.sleep(max(int_t - (time.monotonic()-data_t0),0))

        # get, log and save data
        try:
          data_t0 = time.monotonic()
          data_t,data_v = self._get_data()
          self._logger.log_values(data_t,data_v)
          #s =  time.monotonic()
          m_data.add(data_v)
          #print("#add: %f" % (time.monotonic()-s))
          samples += 1
        except StopIteration:
          stop = True
          break

        # check and process key
        if self._app.key_events:
          key = self._app.key_events.is_key_pressed(
                                           self._app.key_events.KEYMAP_ACTIVE)
          if key == 'TOGGLE' and self._app.display:
            # switch to next view
            c_view = (c_view+1) % len(self._views)
          elif key == 'STOP':
            stop = True
            break
      if stop:
        break

      # update display with current values
      if self._app.display and self._settings.update:
        if self._settings.plots:
          # update plots
          #s =  time.monotonic()
          for i,value in enumerate(data_v):
            self._views[2+i].set_values([value])
          #print("#display plots: %f" % (time.monotonic()-s))
        #s =  time.monotonic()
        if c_view == 0:
          # measurement values
          self._views[c_view].set_values(data_v,time.monotonic()-start_t)
        elif c_view == 1:
          # elapsed time
          self._views[c_view].set_values([time.monotonic()-start_t,
                                           self._settings.duration],-1)
        #print("#display values: %f" % (time.monotonic()-s))
        #s =  time.monotonic()
        self._views[c_view].show()
        if not self._app.key_events:
          # auto toggle view
          c_view = (c_view+1) % len(self._views)
        #print("#display show: %f" % (time.monotonic()-s))

    # that's it, save and log results
    self._app.results.time    = data_t - start_t
    self._app.results.samples = samples
    self._app.results.values  = m_data.get()

    self._logger.log_summary(samples)
