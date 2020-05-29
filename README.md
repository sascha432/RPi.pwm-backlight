# RPi.pwm-backlight

Backlight monitor is a daemon that monitors the backlight GPIO and dims the display using PWM, or just turns it on or off.

## Requirements

Requires systemd, python3 and pigpiod.

## Installation

Check `backlight_monitor.py --help` for available arguments and modify `systemd/backlight-monitor.service` accordingly.

Then run `setup.sh`

`systemctl stop backlight-monitor` stops the service and turns the backlight on.

## Debugging

Stop the backlight-monitor service and execute `backlight_monitor.py 1023 0 -v` to see what's going on.

## gpio-backlight

To activate the backlight overlay, disable display power management and enable the screen saver

`xset -dpms`

`xset s 10`

The backlight should dim after 10 seconds and turn on if any activity is detected. Increase the value "10" as desired.

## Manual control

To enable or disable the backlight, you can send a signal to the daemon.

`kill -USR1 $(pgrep -f backlight_monitor.py)` # turn display on

`kill -USR2 $(pgrep -f backlight_monitor.py)` # turn display off

## Usage

`# backlight_monitor.py --help`

```
usage: backlight_monitor.py [-h] [-P GPIO] [-M MONITORED_GPIO] [--invert]
                            [-f FADE] [-F FREQUENCY] [-DU] [-v] [-i]
                            level_on level_off

Backlight monitoring daemon

positional arguments:
  level_on              backlight level 0-1023
  level_off             backlight level 0-1023

optional arguments:
  -h, --help            show this help message and exit
  -P GPIO, --gpio GPIO  GPIO port (default: 18)
  -M MONITORED_GPIO, --monitored-gpio MONITORED_GPIO
                        GPIO port to monitor (default: 20)
  --invert, --active-low
                        active low for monitored GPIO pin (default: False)
  -f FADE, --fade FADE  Fade delay in seconds (default: 5.0)
  -F FREQUENCY, --frequency FREQUENCY
                        Backlight PWM frequency 100-1000 Hz (default: 200)
  -DU, --disable-user-signals
                        Disable signal USR1/USR2 to turn backlight on and off
                        (default: False)
  -v, --verbose         Verbose output (default: False)
  -i, --info            Display settings and exit (default: False)
```

## Display settings, status and exit

`# backlight_monitor.py 1023 0 -i`

```
on level=750
off level=0
PWM range 0-1023
fading time 5.0s
backlight PWM gpio#18
monitored gpio#20 (active-high)
monitored gpio#20 state=0
backlight level=0, state=off
backlight is off
backlight PWM frequency is 200Hz
real PWM range 1000
signal USR1/USR2 enabled
exiting...
```
