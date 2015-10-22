# -*- coding: utf-8 -*-
"""
ioHub
.. file: ioHub/devices/wintab/__init__.py

Copyright (C) 2012-2015 iSolver Software Solutions
Distributed under the terms of the GNU General Public License (GPL version 3 or any later version).

.. moduleauthor:: Sol Simpson <sol@isolver-software.com>
.. fileauthor:: Sol Simpson <sol@isolver-software.com>
"""

#
### TODO List
#
#   1) Use full screen psychopy experiment window info when creating
#      wintab shadow window
#
#   2) Add settings to device that allow user to specify hardware config values
#      for tablet and tablet context.
#
#   3) Refactor code so that wintab.__init__.py and win32.py are separated
#      in a more sensible way
#
#   4) Allow experiment to check if tablet device was successfully found
#      and started, instead of creating print2err msg's.
#
#   4) Check for missing serial numbers in PACKET evt stream.
#
_is_epydoc=False

# Pen digitizers /tablets that support Wintab API
import gevent
from psychopy.iohub import Computer, Device,print2err
from ...constants import EventConstants, DeviceConstants
import numpy as N

class WintabTablet(Device):
    """
    The Wintab class docstr TBC

    """
    EVENT_CLASS_NAMES=['WintabTabletSampleEvent',]

    DEVICE_TYPE_ID=DeviceConstants.WINTABTABLET
    DEVICE_TYPE_STRING='WINTABTABLET'

    __slots__=['_wtablets',
               '_wtab_shadow_windows',
               '_wtab_canvases'
    ]
    def __init__(self,*args,**kwargs):
        Device.__init__(self,*args,**kwargs['dconfig'])
        self._wtablets=[]
        self._wtab_shadow_windows=[]
        self._wtab_canvases=[]
        self._init_wintab()

    def _init_wintab(self):

        from .win32 import get_tablets
        self._wtablets = get_tablets()
        index = self.getConfiguration().get('device_number',0)

        if len(self._wtablets) == 0:
            self._setHardwareInterfaceStatus(False,
                                             u"Error: No WinTab Devices"
                                             u" Detected.")
            return False
        elif index >= len(self._wtablets):
            self._setHardwareInterfaceStatus(False,
                                             u"Error: device_number {} "
                                             u"is out of range. Only {} "
                                             u"WinTab devices detected.".
                                             format(index, len(self._wtablets)))
            return False

        name = self._wtablets[index].name

        exp_screen_info = self._display_device.getRuntimeInfo()
        swidth, sheight = exp_screen_info.get('pixel_resolution',[None, None])
        screen_index = exp_screen_info.get('index',0)
        if swidth is None:
            self._setHardwareInterfaceStatus(False,
                                             u"Error: Wintab device is"
                                             u" unable to query experiment "
                                             u"screen pixel_resolution.")
            return False

        from pyglet.window import Window
        self._wtab_shadow_windows.append(
            Window(width=1920, height=1080, visible=False, fullscreen=True,
                   vsync=False, screen=screen_index))
        self._wtab_shadow_windows[0].set_mouse_visible(False)
        self._wtab_shadow_windows[0].switch_to()

        from pyglet import app
        app.windows.remove(self._wtab_shadow_windows[0])

        try:
            self._wtab_canvases.append(
                self._wtablets[index].open(self._wtab_shadow_windows[0],self ))
        except Exception, e:
            self._setHardwareInterfaceStatus(False,
                                             u"Error: Unable to create"
                                             u"WintabTabletCanvas for device."
                                             u"Exception: {}".
                                             format(e))
            return False

        self._setHardwareInterfaceStatus(True)
        return True

    def getHarwareConfig(self, index=0):
        return {"WinTabContext":self._wtab_canvases[index].getContextInfo(),
                 "WintabHardwareInfo":self._wtablets[index].hw_axis_info
                }

    def enableEventReporting(self,enabled=True):
        for wtc in self._wtab_canvases:
            wtc.enable(enabled)
        return Device.enableEventReporting(self, enabled)

    def _poll(self):
        try:
            for swin in self._wtab_shadow_windows:
                swin.dispatch_events()
            logged_time = Computer.getTime()

            if not self.isReportingEvents():
                self._last_poll_time = logged_time
                for wtc in self._wtab_canvases:
                    del wtc._iohub_events[:]
                return False

            confidence_interval = self._last_poll_time - logged_time
            #TODO: Determine if delay can be calculated.
            #      Using 0 for now as it is unknown.
            delay = 0.0

            for wtc in self._wtab_canvases:
                for wte in wtc._iohub_events:
                    self._addNativeEventToBuffer((logged_time,
                                                  delay,
                                                  confidence_interval,
                                                  wte))

                del wtc._iohub_events[:]
            self._last_poll_time = logged_time
            return True
        except Exception, e:
            print2err("ERROR in WintabTabletDevice._poll: ",e)

    def _getIOHubEventObject(self,native_event_data):
        '''

        :param native_event_data:
        :return:
        '''
        logged_time, delay, confidence_interval, wt_event = native_event_data
        device_time = wt_event.pop(0)
        evt_status = wt_event.pop(0)

        #TODO: Correct for polling interval / CI when calculating iohub_time
        iohub_time = logged_time

        ioevt=[0, 0, 0, Computer._getNextEventID(),
               EventConstants.WINTAB_TABLET_SAMPLE,
               device_time,
               logged_time,
               iohub_time,
               confidence_interval,
               delay,
               0
            ]
        ioevt.extend(wt_event)
        return ioevt

    def _close(self):
        for wtc in self._wtab_canvases:
            wtc.close()
        for swin in self._wtab_shadow_windows:
            swin.close()
        Device._close()

from .win32 import get_tablets

############# Wintab Event Classes ####################

from .. import DeviceEvent

class WintabTabletInputEvent(DeviceEvent):
    """
    The MouseInputEvent is an abstract class that is the parent of all MouseInputEvent types
    that are supported in the ioHub. Mouse position is mapped to the coordinate space
    defined in the ioHub configuration file for the Display.
    """
    PARENT_DEVICE=WintabTablet
#    EVENT_TYPE_STRING='WINTAB_TABLET_INPUT'
#    EVENT_TYPE_ID=EventConstants.WINTAB_TABLET_INPUT
#    IOHUB_DATA_TABLE=EVENT_TYPE_STRING

    _newDataTypes = [
                     ('display_id',N.uint8),     # gives the display index for the event.
                     ('window_id',N.uint64)      # window ID for the event
                                                 # must be an invisible window created by device
                    ]

    __slots__=[e[0] for e in _newDataTypes]
    def __init__(self,*args,**kwargs):

        #: The id of the display that the mouse was over when the event occurred.
        #: Only supported on Windows at this time. Always 0 on other OS's.
        self.display_id=None

        #: Window handle reference that the mouse was over when the event occurred
        #: (window does not need to have focus)
        self.window_id=None

        DeviceEvent.__init__(self, *args, **kwargs)

#    @classmethod
#    def _convertFields(cls,event_value_list):
#        modifier_value_index=cls.CLASS_ATTRIBUTE_NAMES.index('modifiers')
#        event_value_list[modifier_value_index]=KeyboardConstants._modifierCodes2Labels(event_value_list[modifier_value_index])

#    @classmethod
#    def createEventAsDict(cls,values):
#        cls._convertFields(values)
#        return dict(zip(cls.CLASS_ATTRIBUTE_NAMES,values))

#    #noinspection PyUnresolvedReferences
#    @classmethod
#    def createEventAsNamedTuple(cls,valueList):
#        cls._convertFields(valueList)
#        return cls.namedTupleClass(*valueList)

class WintabTabletSampleEvent(WintabTabletInputEvent):
    """
    MouseMoveEvent's occur when the mouse position changes. Mouse position is
    mapped to the coordinate space defined in the ioHub configuration file
    for the Display.

    Event Type ID: EventConstants.MOUSE_MOVE

    Event Type String: 'MOUSE_MOVE'
    """
    EVENT_TYPE_STRING='WINTAB_TABLET_SAMPLE'
    EVENT_TYPE_ID=EventConstants.WINTAB_TABLET_SAMPLE
    IOHUB_DATA_TABLE=EVENT_TYPE_STRING

    _newDataTypes = [
                     ('serial_number', N.uint),
                     ('cursor',N.uint32),
                     ('buttons',N.int32),
                     ('x',N.int32),
                     ('y',N.int32),
                     ('z',N.int32),
                     ('pressure_normal',N.uint32),
                     ('pressure_tangent',N.uint32),
                     ('orient_azimuth',N.int32),
                     ('orient_altitude',N.int32),
                     ('orient_twist',N.int32),
                     ('rotation_pitch',N.int32),
                     ('rotation_roll',N.int32),
                     ('rotation_yaw',N.int32)
                     ]

    __slots__=[e[0] for e in _newDataTypes]
    def __init__(self, *args, **kwargs):
        #: serial_number Hardware assigned PACKET serial number
        self.serial_number=None

        #: TODO: cursor
        self.cursor=None

        #: TODO: buttons
        self.buttons=None

        #: x Horizontal position of stylus on tablet surface.
        self.x=None

        #: y Vertical position of stylus on tablet surface.
        self.y=None

        #: z Distance of stylus tip from tablet surface
        #: Supported on Wacom Intuos4; other device support unknown.
        #: Value will between 0 and max_val, where max_val is usually 1024.
        #: A value of 0 = tip touching surface, while
        #: max_val = tip height above surface before events stop being reported.
        self.z=None

        #: pressure_normal Normalize pressure of stylus tip on tablet surface.
        #: Value will range from 0 - 1.0, where 1.0 is maximum pressure
        self.pressure_normal=None

        #: pressure_tangent
        self.pressure_tangent=None

        #: orient_azimuth
        self.orient_azimuth=None

        #: orient_altitude
        self.orient_altitude=None

        #: orient_twist
        self.orient_twist=None

        #: rotation_pitch
        self.rotation_pitch=None

        #: rotation_roll
        self.rotation_roll=None

        #: rotation_yaw
        self.rotation_yaw=None

        WintabTabletInputEvent.__init__(self, *args, **kwargs)