# -*- coding: utf-8 -*-
"""
ioHub
.. file: ioHub/devices/serial/__init__.py

Copyright (C) 2012-2014 iSolver Software Solutions
Distributed under the terms of the GNU General Public License (GPL version 3 or any later version).

.. moduleauthor:: Sol Simpson <sol@isolver-software.com> + contributors, please see credits section of documentation.
.. fileauthor:: Sol Simpson <sol@isolver-software.com>
"""
from psychopy.iohub import Computer
from .. import Device
from ...constants import DeviceConstants
getTime = Computer.getTime
import pphelper

class Olfactometer(Device):
    DEVICE_TIMEBASE_TO_SEC = 1.0
    DEVICE_TYPE_ID = DeviceConstants.OLFACTOMETER
    DEVICE_TYPE_STRING = "OLFACTOMETER"
    __slots__ = ['_olfactometer']

    def __init__(self, *args, **kwargs):
        Device.__init__(self, *args, **kwargs['dconfig'])
        self._olfactometer =  pphelper.hardware.Olfactometer(
            ni_lines='Dev1/port0/line0:7',
            ni_trigger_line=None,
            ni_task_name='Olfactometer'
        )

    def getDeviceTime(self):
        return getTime()

    def getSecTime(self):
        """
        Returns current device time in sec.msec format.
        Relies on a functioning getDeviceTime() method.
        """
        return self.getTime()

    def addStimulus(self, *args, **kwargs):
        self._olfactometer.add_stimulus(*args, **kwargs)

    def selectStimulus(self, name):
        self._olfactometer.select_stimulus(name)

    def removeStimulus(self, name):
        self._olfactometer.remove_stimulus(name)

    def stimulate(self):
        self._olfactometer.stimulate()

    def stimulus(self):
        stimulus = self._olfactometer.stimulus
        stimulus['bitmask'] = [int(x) for x in stimulus['bitmask']]
        stimulus['bitmask_offset'] = [int(x) for x in stimulus['bitmask_offset']]

        return stimulus

    def stimuli(self):
        stimuli = []
        for stimulus in self._olfactometer.stimuli:
            stimulus['bitmask'] = [int(x) for x in stimulus['bitmask']]
            stimulus['bitmask_offset'] = [int(x) for x in stimulus['bitmask_offset']]
            stimuli.append(stimulus)

        return stimuli
