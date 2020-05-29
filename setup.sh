#!/bin/bash

DEPS="/usr/bin/python3 backlight_monitor.py systemd/backlight-monitor.service /sys/class/backlight/gpio-backlight/bl_power
"

function failure {
    echo "Installation failed: $@"
    exit 1
}

for FILE in $DEPS ; do
    if [ ! -f "$FILE" ] ; then
        failure "$FILE not found"
    fi
done

function systemctl_enable_and_start {
    systemctl enable "$1" &> /dev/null || failure "Failed to enable $1.service"
    systemctl start "$1" &> /dev/null || failure "Failed to start $1.service"
}

function install_piugpiod {
    apt install pigpiod || failure "Failed to install pigpiod"
    systemctl_enable_and_start pigpiod
}

function copy {
    cp "$1" "$2" || failure "Failed to copy $1 to $2"
}

apt list pigpiod 2>&1 | grep -q "\[installed\]" && echo "pigpiod already is installed" || install_pigpiod
systemctl stop backlight-monitor &> /dev/null && echo "backlight-monitor.service stopped"
copy backlight_monitor.py /usr/local/bin
chmod 755 /usr/local/bin/backlight_monitor.py
copy systemd/backlight-monitor.service /etc/systemd/system
systemctl_enable_and_start backlight-monitor
systemctl is-active backlight-monitor &> /dev/null && echo -e "backlight-monitor.service started\nSuccess!" || echo "Failed to start backlight-monitor.service"
