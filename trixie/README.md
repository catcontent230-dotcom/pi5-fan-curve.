# Pi 5 Fan Curve Studio — Trixie Edition

A redesigned Raspberry Pi 5 fan-curve GUI for the current Raspberry Pi OS release line. This is a separate edition; it does not replace the original project files.

## Target platform

- Raspberry Pi 5 with its official four-pin fan connector and a supported fan/cooler
- Raspberry Pi OS 64-bit (Debian Trixie, kernel 6.18 release dated 6 October 2026)
- Python 3 and Tkinter

The app uses the Pi 5 firmware/device-tree parameters `cooling_fan` and `fan_temp0`–`fan_temp3` (plus the corresponding `_hyst` and `_speed` values). The firmware handles fan control; this edition does not run a polling daemon or write to `/sys/class/thermal/cooling_device*`.

## Install and run

```bash
sudo apt update
sudo apt install -y python3-tk
python3 pi5_fan_curve_trixie.py
```

## Use

1. Edit the four temperature thresholds, PWM values (0–255), and hysteresis values.
2. Keep thresholds increasing and fan power non-decreasing; the app validates these constraints.
3. Select **Apply to boot config** and approve the administrator prompt.
4. The app backs up the boot config once to `config.txt.pi5-fan-backup`, then writes a clearly marked settings block to `/boot/firmware/config.txt` (or `/boot/config.txt` if that is the existing path).
5. Reboot to activate the firmware fan curve.

The app removes existing active fan settings from `dtparam` lines (including comma-separated settings) before writing its own block, avoiding duplicate overrides while preserving unrelated settings.

## Default curve

| Stage | Temperature | PWM | Hysteresis |
|---|---:|---:|---:|
| 1 | 50°C | 75/255 | 5°C |
| 2 | 60°C | 125/255 | 5°C |
| 3 | 67.5°C | 175/255 | 5°C |
| 4 | 75°C | 250/255 | 5°C |

These are Raspberry Pi's documented defaults. PWM is a raw 0–255 setting, not a percentage.

## Important notes

- This is specifically for the Raspberry Pi 5 onboard four-pin fan interface. It is not a generic GPIO fan controller.
- A reboot is required after applying because these are boot-time firmware/device-tree settings.
- Temperature and RPM telemetry depend on the relevant sysfs sensors being exposed. Missing RPM telemetry does not by itself mean fan control is unavailable.
- Test carefully and monitor temperatures after changing the curve. Do not set fan speeds too low for your workload or cooling setup.
- The code has been syntax-checked, but has not been run against your physical Pi or fan hardware. Hardware behavior still needs your test.

## References

- Raspberry Pi OS downloads and release details: https://www.raspberrypi.com/software/operating-systems/
- Raspberry Pi 5 fan behavior and tuning: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- Official firmware overlay parameter reference: https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README
