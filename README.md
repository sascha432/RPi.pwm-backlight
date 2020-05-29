# RPi.pwm-backlight

Backlight monitor is a daemon that monitors the backlight GPIO and dims the display using PWM, or just turns it on or off.

## Requirements

Requires systemd, python3 and pigpiod

## Installation

Check `backlight_monitor.py --help` for available arguments and modify `systemd/backlight-monitor.service` accordingly

Then run `setup.sh`

`systemctl stop backlight-monitor` stops the service and turns the backlight on.

## gpio-backlight

To activate the backlight overlay, disable display power management and enable the screen saver

`xset -dpms`

`xset s 10`

The backlight should dim after 10 seconds and turn on if any activity is detected. Increase the value "10" as desired.

## Manual control

To enable or disable the backlight, you can send a signal to the daemon.

`kill -USR1 $(pgrep -f backlight_monitor.py)` # turn display on

`kill -USR2 $(pgrep -f backlight_monitor.py)` # turn display off
