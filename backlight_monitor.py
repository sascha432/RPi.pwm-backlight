#!/usr/bin/python3

import pigpio
import time
import sys
import argparse
import signal
import threading

class Defaults(object):
    MAX_PWM = 1023
    BACKLIGHT_GPIO = 18
    MONITORED_GPIO = 20
    TOGGLE_GPIO = None
    FREQUENCY = 200
    FREQUENCY_RANGE = (100, 1000)
    FADE_TIME = 5.0
    MAX_FADE_TIME = 60.0
ds = Defaults()

parser = argparse.ArgumentParser(description='Backlight monitoring daemon', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('level_on', metavar='level_on', type=int, help='backlight level 0-%d' % ds.MAX_PWM)
parser.add_argument('level_off', metavar='level_off', type=int, help='backlight level 0-%d' % ds.MAX_PWM)
parser.add_argument('-P', '--gpio', default=ds.BACKLIGHT_GPIO, type=int, help="GPIO pin")
parser.add_argument('-M', '--monitored-gpio', default=ds.MONITORED_GPIO, type=int, help="GPIO pin to monitor")
parser.add_argument('-T', '--toggle-gpio', default=ds.TOGGLE_GPIO, type=int, help="GPIO pin for a push button")
parser.add_argument('--invert', '--active-low', action='store_true', default=False, help="active low for monitored GPIO pin")
parser.add_argument('-f', '--fade', default=ds.FADE_TIME, type=float, help="Fade delay in seconds")
parser.add_argument('-F', '--frequency', default=ds.FREQUENCY, type=int, help="Backlight PWM frequency %d-%d Hz" % ds.FREQUENCY_RANGE)
parser.add_argument('-DU', '--disable-user-signals', action='store_true', default=False, help="Disable signal USR1/USR2 to turn backlight on and off")
parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Verbose output")
parser.add_argument('-i', '--info', action='store_true', default=False, help="Display settings and exit")
args = parser.parse_args()

def verbose(msg):
    if args.verbose:
        print(msg)


args.frequency = min(ds.FREQUENCY_RANGE[1], max(ds.FREQUENCY_RANGE[0], args.frequency))
args.fade = min(ds.MAX_FADE_TIME, max(0, args.fade))
args.level_on = min(ds.MAX_PWM, max(0, args.level_on))
args.level_off = min(ds.MAX_PWM, max(0, args.level_off))
if args.info:
    args.verbose = True

pi = pigpio.pi()

# return True if backlight is on
def is_backlight_on(level):
    state = not args.invert
    if level==0:
        state = not state
    verbose("backlight level=%d, state=%s" % (level, (state and "on" or "off")))
    return state

# read monitored gpio and return if backlight is on
def get_monitored_gpio_state():
    state = pi.read(args.monitored_gpio)
    verbose("monitored gpio#%d state=%d" % (args.monitored_gpio, state))
    return state

# return "on" or "off"
def get_backlight_state():
    return is_backlight_on(get_monitored_gpio_state()) and "on" or "off"

def get_backlight_level(on_error = -1):
    try:
        return pi.get_PWM_dutycycle(args.gpio)
    except:
        return on_error

class FadingThread(threading.Thread):
    def __init__(self, pigpio, backlight_gpio, fade_time, level):
        threading.Thread.__init__(self)
        self.cont = threading.Event()
        self.killed = False
        self.idle = True
        self.direction = 0
        self.pigpio = pigpio
        self.backlight_gpio = backlight_gpio
        self.level = level
        self.target_level = 0
        self.initial_level = 0
        self.fade_delay = fade_time / abs(level[0] - level[1])
        self.verbose("fade delay %dms" % int(self.fade_delay * 1000))

    def verbose(self, msg):
        if (args.verbose):
            print("FadingThread %s" % msg)

    def start(self):
        threading.Thread.start(self)

    def kill(self):
        self.verbose("kill")
        self.killed = True
        self.wakeup()

    def wakeup(self):
        self.verbose("wakeup")
        self.cont.set()

    def fade_to(self, level):
        if not self.idle:
            self.verbose("stopping current operation")
            self.direction = 0
            self.cont.set()
            c = 0
            while not self.idle:
                c = c + 1
                time.sleep(0.01)
            self.verbose("count %d" % c)
        self.target_level = level
        self.initial_level = get_backlight_level(self.target_level)
        self.direction = (self.target_level > self.initial_level) and 1 or -1
        self.verbose("fade from %d to %d (%d)" % (self.initial_level, self.target_level, self.direction))
        self.wakeup()

    def sleep(self, timeout = None):
        if timeout==None:
            self.verbose("sleep mode")
        # else:
        #     self.verbose("delay %dms" % int(timeout * 1000))
        self.cont.clear()
        self.cont.wait(timeout)
        self.cont.clear()
        if self.killed:
            raise StopIteration()

    def run(self):
        try:
            while not self.killed:
                self.idle = True
                self.direction = 0
                self.sleep()
                self.idle = False
                current_level = self.initial_level
                while self.direction!=0 and self.target_level!=current_level:
                    # self.verbose("level %d" % current_level)
                    current_level = current_level + self.direction
                    self.pigpio.set_PWM_dutycycle(self.backlight_gpio, current_level)
                    self.sleep(self.fade_delay)
        except StopIteration:
            self.verbose("terminated")

# set backlight level
def set_backlight(level):
    if args.fade>0:
        ft.fade_to(level)
    else:
        pi.set_PWM_dutycycle(args.gpio, level)

# callback for monitored gpio
def mon_callback(gpio, level, tick):
    new_level = is_backlight_on(level) and args.level_on or args.level_off
    verbose("monitored gpio#%d level=%d, set backlight=%d" % (gpio, level, new_level))
    set_backlight(new_level)

# callback for toggle button gpio
def toggle_callback(gpio, level, tick):
    cur_level = get_backlight_level()
    if cur_level==args.level_on:
        new_level = args.level_off
    else:
        new_level = args.level_on
    verbose("toggle gpio#%d current level=%d, set backlight=%d" % (gpio, cur_level, new_level))
    set_backlight(new_level)

# turn display on if script is terminated
def term_signal_handler(sig, frame):
    verbose('signal %d, exiting...' % sig)
    ft.kill()
    verbose("turning backlight on")
    pi.set_PWM_dutycycle(args.gpio, args.level_on)
    sys.exit(sig)

# handler for other signals
def signal_handler(sig, frame):
    if sig==signal.SIGUSR1:
        verbose("signal USR1, turning display on")
        set_backlight(args.level_on)
    elif sig==signal.SIGUSR2:
        verbose("signal USR2, turning display off")
        set_backlight(args.level_off)

### main

pi.set_PWM_range(args.gpio, ds.MAX_PWM)
res = pi.set_PWM_frequency(args.gpio, args.frequency)
if res!=args.frequency:
    print('Failed to set PWM frequency to %d' % args.frequency)
    print('Suggested frequency: %d' % res)
    sys.exit(1)

verbose("on level=%d" % args.level_on)
verbose("off level=%d" % args.level_off)
verbose("PWM range 0-%d" % pi.get_PWM_range(args.gpio))
verbose("fading %s" % (args.fade and ("time " + str(args.fade) + "s") or "is off"))
verbose("backlight PWM gpio#%d" % args.gpio)
verbose("monitored gpio#%d%s" % (args.monitored_gpio, (args.invert and " (active-low)" or " (active-high)")))
verbose("toggle button %s" % (args.toggle_gpio and " gpio#" + str(args.toggle_gpio) or "disabled"))
verbose("backlight is %s" % get_backlight_state())
verbose('backlight PWM frequency is %dHz' % args.frequency)
verbose("real PWM range %d" % pi.get_PWM_real_range(args.gpio))
verbose('signal USR1/USR2 %s' % (args.disable_user_signals and "disabled" or "enabled"))

if args.info:
    verbose("exiting...")
    sys.exit(0)

if args.fade>0:
    ft = FadingThread(pi, args.gpio, args.fade, [args.level_off, args.level_on])
    ft.start()

# set initial state during startup
mon_callback(args.monitored_gpio, pi.read(args.monitored_gpio), 0)

verbose("monitoring gpio#%d" % args.monitored_gpio)
pi.callback(args.monitored_gpio, pigpio.EITHER_EDGE, mon_callback)

if args.toggle_gpio:
    verbose("toggle button gpio#%d" % args.toggle_gpio)
    pi.callback(args.toggle_gpio, pigpio.RISING_EDGE, toggle_callback)

signal.signal(signal.SIGINT, term_signal_handler)
signal.signal(signal.SIGTERM, term_signal_handler)
if not args.disable_user_signals:
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)

if args.verbose:
    while True:
        verbose("backlight is %s" % get_backlight_state())
        time.sleep(5)
