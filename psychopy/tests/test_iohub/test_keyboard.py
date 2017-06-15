""" Test ioHub Keyboard Device & Events
"""
from copy import copy
import time

from psychopy.tests.utils import skip_under_travis
from psychopy.tests.test_iohub.testutil import startHubProcess, stopHubProcess, getTime
import logging

@skip_under_travis
class TestKeyboard(object):
    """
    Keyboard Device tests. Starts iohub server, runs test set, then
    stops iohub server.

    Since there is no way to currently automate keyboard event generation in
    a way that would actually test the iohub keyboard event processing logic,
    each test simply calls one of the device methods / properties and checks
    that the return type is as expected.

    Each method is called with no args; that should be improved.
    """

    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """

        # iohub_config = {}
        # Uncomment config to use iosync keyboard to test
        # iohub keyboard device. An ioSync device must be connected to
        # a USB 2.0 port on the computer running the tests.
        iohub_config = {'mcu.iosync.MCU': dict(serial_port='auto',
                                               monitor_event_types=[]
                                               )
                        }

        cls.io = startHubProcess(iohub_config)
        cls.keyboard = cls.io.devices.keyboard
        cls.iosync = cls.io.getDevice('mcu')
        #assert cls.iosync is not None
        if cls.iosync and not cls.iosync.isConnected():
            #assert iosync is not None, "iosync device requested but devvice is None."
            #assert iosync.isConnected(), "iosync device requested but isConnected() == False"
            cls.iosync = None

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        stopHubProcess()
        cls.io = None
        cls.keyboard = None
        cls.iosync = None

    def get_kb_events(self, kb_get_method, loop_dur, **kbkwargs):
        stime = getTime()
        kb_events = []
        while getTime() - stime < loop_dur:
            kbes = kb_get_method(**kbkwargs)
            if kbes:
                kb_events.extend(kbes)
        return kb_events

    def validate_kb_event(self, kbe, is_press, ekey, echar, emods=[],
                          edur=None, kbpress=None):
        emods = copy(emods)

        if is_press:
            assert kbe.type == 'KEYBOARD_PRESS'
        else:
            assert kbe.type == 'KEYBOARD_RELEASE'

        assert kbe.key == ekey
        assert kbe.char == echar
        assert kbe == ekey and kbe == echar

        kbe_mods = copy(kbe.modifiers)
        if kbe_mods:
            numlock_active = len(kbe_mods) == 1 and kbe_mods[0] == 'numlock'
            if numlock_active and 'numlock' not in emods:
                emods.append('numlock')
        for m in kbe.modifiers:
            try:
                kbe_mods.remove(m)
            except:
                pass
        fail_str_ = "Unexpected modifiers found: {}. KeyboardEvent: {}"
        assert len(kbe_mods) == 0, fail_str_.format(kbe_mods, kbe)

        if kbe.type == 'KEYBOARD_RELEASE':
            dt = None
            if kbpress:
                assert kbpress.id == kbe.pressEventID
                assert kbpress.time < kbe.time
                dt = kbe.time - kbpress.time
                assert dt - kbe.duration == 0.0
            if edur is not None:
                mindur = edur-0.005
                maxdur = edur+0.005
                if dt:
                    assert mindur < dt < maxdur
                assert mindur < kbe.duration < maxdur

    def test_getEvents(self):
        self.io.clearEvents()
        evts = self.keyboard.getEvents()
        assert isinstance(evts, (list, tuple))

    def test_getKeys(self):
        # getKeys(self, keys=None, chars=None, mods=None, duration=None,
        #         etype = None, clear = True)
        self.io.clearEvents()
        if self.iosync:
            # Use iosync as keyboard device to generate actual keyboard
            # events so iohub event fields can be checked for accuracy.

            # 'a' key pressed on iosync keyboard with no modifiers. Key is
            # released after 0.2 seconds.
            pressed_dur = 0.2
            self.iosync.generateKeyboardEvent('a', [], pressed_dur)

            # Call self.keyboard.getKeys() repeatedly for 0.3 seconds
            # and return any events received from getKeys() during that
            # time period
            kb_events = self.get_kb_events(self.keyboard.getKeys,
                                           pressed_dur + 0.1)

            # The two 'a' key press and release events should have been
            # reported by iohub.
            assert len(kb_events) == 2
            kp = kb_events[0]
            kr = kb_events[1]
            # Validate each event contains the expected values.
            self.validate_kb_event(kp, is_press=True, ekey='a', echar=u'a')
            self.validate_kb_event(kr, is_press=False, ekey='a', echar=u'a',
                                   edur=pressed_dur, kbpress=kp)
        else:
            # No keyboard events are generated, so we can only check that
            # .getKeys() runs without error and returns an empty list.
            evts = self.keyboard.getKeys()
            assert isinstance(evts, (list, tuple))

    def test_getPresses(self):
        # getPresses(self, keys=None, chars=None, mods=None, clear=True)
        self.io.clearEvents()
        if self.iosync:
            self.iosync.generateKeyboardEvent('b', [], 0.1)
            kb_events = self.get_kb_events(self.keyboard.getPresses, 0.2)

            assert len(kb_events) == 1
            self.validate_kb_event(kb_events[0], is_press=True, ekey='b',
                                   echar=u'b')
        else:
            evts = self.keyboard.getPresses()
            assert isinstance(evts, (list, tuple))

    def test_getReleases(self):
        # getReleases(self, keys=None, chars=None, mods=None, duration=None,
        #             clear = True)
        self.io.clearEvents()
        if self.iosync:
            pressed_dur = 0.2
            self.iosync.generateKeyboardEvent('c', [], pressed_dur)


            kb_releases = self.get_kb_events(self.keyboard.getReleases,
                                             pressed_dur + 0.1)
            assert len(kb_releases) == 1,[(e.time, e.type, e.key) for e in kb_releases]

            kb_presses = self.keyboard.getPresses()
            assert len(kb_presses) == 1

            self.validate_kb_event(kb_releases[0], is_press=False, ekey='c',
                                   echar=u'c', edur=pressed_dur,
                                   kbpress=kb_presses[0])
        else:
            evts = self.keyboard.getReleases()
            assert isinstance(evts, (list, tuple))

    def test_waitForKeys(self):
        # waitForKeys(maxWait, keys, chars, mods, duration, etype, clear,
        #             checkInterval)
        self.io.clearEvents()
        if self.iosync:
            pressed_dur = 0.1
            self.iosync.generateKeyboardEvent('d', [], pressed_dur)
            time.sleep(pressed_dur+0.05)
            self.iosync.generateKeyboardEvent('e', [], pressed_dur)
            time.sleep(pressed_dur+0.05)

            kb_events = self.keyboard.waitForKeys()

            assert len(kb_events) == 4
            kp_d, kr_d, kp_e, kr_e = kb_events

            self.validate_kb_event(kp_d, is_press=True, ekey='d', echar=u'd')
            self.validate_kb_event(kr_d, is_press=False, ekey='d', echar=u'd',
                                   edur=pressed_dur, kbpress=kp_d)
            self.validate_kb_event(kp_e, is_press=True, ekey='e', echar=u'e')
            self.validate_kb_event(kr_e, is_press=False, ekey='e', echar=u'e',
                                   edur=pressed_dur, kbpress=kp_e)
        else:
            evts = self.keyboard.waitForKeys(maxWait=0.05)
            assert isinstance(evts, (list, tuple))

    def test_waitForPresses(self):
        # waitForPresses(self, maxWait=None, keys=None, chars=None,
        #                mods = None, duration = None, clear = True,
        #                checkInterval = 0.002)
        self.io.clearEvents()
        if self.iosync:
            pressed_dur = 0.1
            self.iosync.generateKeyboardEvent('f', [], pressed_dur)
            time.sleep(pressed_dur + 0.05)
            self.iosync.generateKeyboardEvent('g', [], pressed_dur)
            time.sleep(pressed_dur + 0.05)
            self.iosync.generateKeyboardEvent('h', [], pressed_dur)
            time.sleep(0.01)

            stime = getTime()
            kb_events = self.keyboard.waitForPresses(keys=['f'])
            wtime = getTime() - stime

            # Should get both 'f' press event only
            assert len(kb_events) == 1
            # Should not have had to wait much at all to get it,
            # since it already occurred
            assert wtime < 0.005
            self.validate_kb_event(kb_events[0], is_press=True, ekey='f',
                                   echar=u'f')

            # Calling wait for presses again should return the 'g' event since
            # the previous call only returned the matching event 'f'.
            stime = getTime()
            kb_events = self.keyboard.waitForPresses(keys=['g'], maxWait=0.1)
            wtime = getTime() - stime
            assert len(kb_events) == 1
            self.validate_kb_event(kb_events[0], is_press=True, ekey='g',
                               echar=u'g')
            # Should not have had to wait much at all to get it,
            # since it already occurred
            assert wtime < 0.005

            # 'h' press event is still in Keyboard buffer,
            # lets clear all iohub event buffers and see what happens...
            self.io.clearEvents()

            # So now there should be nothing left in kb buffer
            stime = getTime()
            kb_events = self.keyboard.waitForPresses(maxWait=0.1)
            wtime = getTime() - stime
            assert len(kb_events) == 0
            # waitForPresses() call should have taken 0.1 sec
            assert 0.095 < wtime < 0.105
        else:
            evts = self.keyboard.waitForPresses(maxWait=0.05)
            assert isinstance(evts, (list, tuple))

    def test_waitForReleases(self):
        # waitForReleases(self, maxWait=None, keys=None, chars=None,
        #                 mods = None, duration = None, clear = True,
        #                 checkInterval = 0.002)
        self.io.clearEvents()
        if self.iosync:
            pressed_dur = 0.2
            self.iosync.generateKeyboardEvent('i', [], pressed_dur)
            kb_events = self.keyboard.waitForReleases(maxWait=0.1,
                                                      keys=['i', 'j'])
            # Waited only 0.1 sec, when keypress duration will be 0.2 sec,
            # so key should not have been released yet and waitForReleases()
            # should return 0 events
            assert len(kb_events) == 0

            # Now wait for another 0.2 sec to get keyboard release events
            stime = getTime()
            kb_events = self.keyboard.waitForReleases(maxWait=0.2,
                                                      keys=['i', 'j'])
            wtime = getTime() - stime

            # the single release event should have been received
            assert len(kb_events) == 1
            # and the call to waitForReleases should have returned in
            # about 0.1 sec
            assert 0.090 < wtime < 0.11
            self.validate_kb_event(kb_events[0], is_press=False,
                                   ekey='i', echar=u'i')


            self.iosync.generateKeyboardEvent('j', [], pressed_dur)
            kb_events = self.keyboard.waitForReleases(keys=['i', 'j'])

            assert len(kb_events) == 1

            self.validate_kb_event(kb_events[0], is_press=False,
                                   ekey='j', echar=u'j')
        else:
            evts = self.keyboard.waitForReleases(maxWait=0.05)
            assert isinstance(evts, (list, tuple))

    def test_clearKeyboardEvents(self):
        self.io.clearEvents()
        if self.iosync:
            pressed_dur = 0.1
            self.iosync.generateKeyboardEvent('k', [], pressed_dur)
            time.sleep(pressed_dur+0.2)

            self.keyboard.clearEvents()

            kb_evts = self.keyboard.getEvents()
            io_evts = self.io.getEvents()
            assert len(kb_evts) == 0
            assert len(io_evts) == 2

            kb_evts = self.keyboard.getEvents()
            io_evts = self.io.getEvents()
            assert len(kb_evts) == 0
            assert len(io_evts) == 0
        else:
            self.keyboard.clearEvents()
            assert len(self.keyboard.getEvents()) == 0

    def test_clearAllEvents(self):
        self.io.clearEvents()
        if self.iosync:
            pressed_dur = 0.1
            self.iosync.generateKeyboardEvent('l', [], pressed_dur)
            time.sleep(pressed_dur + 0.2)

            self.io.clearEvents()

            kb_evts = self.keyboard.getEvents()
            io_evts = self.io.getEvents()
            assert len(kb_evts) == 0
            assert len(io_evts) == 0
        else:
            self.io.clearEvents()
            assert len(self.keyboard.getEvents()) == 0

    def test_state(self):
        if self.iosync:
            assert isinstance(self.keyboard.state, dict)

            pressed_dur = 0.2
            self.iosync.generateKeyboardEvent('m', [], pressed_dur)
            time.sleep(0.005)

            # keyboard.state should include 'm' key since it is currently
            # pressed
            kbstate = self.keyboard.state
            assert 'm' in kbstate

            # clearing event buffers does not effect keyboard state
            self.io.clearEvents()
            self.keyboard.clearEvents()

            kbstate = self.keyboard.state
            assert 'm' in kbstate

            time.sleep(0.2)

            self.iosync.generateKeyboardEvent('n', [], pressed_dur)
            time.sleep(0.005)

            # keyboard.state should not include 'm' key anymore, but should
            # include 'n' since it is currently pressed
            kbstate = self.keyboard.state
            assert 'm' not in kbstate
            assert 'n' in kbstate

        else:
            kbstate = self.keyboard.state
            assert isinstance(kbstate, dict)
            assert len(kbstate.keys()) == 0

    def test_reporting(self):

        assert self.keyboard.reporting is True,  "Reporting is not True: {}, {}".format(type(self.keyboard.reporting),  self.keyboard.reporting)
        assert self.keyboard.isReportingEvents() is True
        if self.iosync:
            self.iosync.generateKeyboardEvent('o', [], 0.1)
            kb_evts = self.keyboard.waitForReleases()
            # since kb reporting is enabled, should have received 1 evt
            assert len(kb_evts) == 1

        self.keyboard.reporting = False
        assert self.keyboard.reporting is False
        assert self.keyboard.isReportingEvents() is False
        self.keyboard.clearEvents()
        if self.iosync:
            self.iosync.generateKeyboardEvent('p', [], 0.1)
            kb_evts = self.keyboard.waitForKeys(maxWait=0.2)
            # since kb reporting is disabled, should have received 1 evt
            assert len(kb_evts) == 0

        self.keyboard.reporting = True
        assert self.keyboard.reporting is True
        assert self.keyboard.isReportingEvents() is True
        if self.iosync:
            self.iosync.generateKeyboardEvent('q', [], 0.1)
            kb_evts = self.keyboard.waitForReleases()
            # since kb reporting is enabled, should have received 1 evt
            assert len(kb_evts) == 1

