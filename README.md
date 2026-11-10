# Raspberry Pi 5 Fan Curve Editor

Fan-curve software for a Raspberry Pi 5 with a compatible fan connected to the official four-pin fan connector.

**This repository contains two architecture-specific editions. Choose the one matching your installed OS — do not mix them.**

## Choose your edition

| Edition | Use it on | Control method | Reboot after applying? |
|---|---|---|---|
| **Original 32-bit Edition** | Raspberry Pi OS 32-bit (32-bit Python userspace) | systemd service controls a Linux thermal fan cooling-device interface | Normally no |
| **Trixie 64-bit Edition — Fan Curve Studio** | Raspberry Pi OS 64-bit Trixie on Raspberry Pi 5 | Pi 5 firmware fan-curve settings in the boot config | Yes |

The apps check the Python runtime architecture when they start. The original GUI and daemon require 32-bit Python. The Trixie GUI requires 64-bit Python.

Check your OS architecture with `getconf LONG_BIT`. A result of `32` means use the Original 32-bit Edition. A result of `64` means use the Trixie 64-bit Edition, provided you are running Raspberry Pi OS Trixie on a Pi 5.

This project targets the supported Pi 5 fan connector. It is not a generic GPIO fan controller.

## Get the files

[Open the public GitHub repository](https://github.com/catcontent230-dotcom/pi5-fan-curve.)

Clone it onto your Pi:

```bash
git clone https://github.com/catcontent230-dotcom/pi5-fan-curve..git
cd pi5-fan-curve.
```

The repository name itself ends with a full stop. The two full stops before `.git` in the clone URL are intentional. Cloning only downloads the files; it does not install or start a controller.

## Original Edition — 32-bit Raspberry Pi OS

Use only with a 32-bit OS / 32-bit Python environment. Files: `fan_curve_editor.py` (GUI) and `fan_daemon.py` (background service).

Requirements: Raspberry Pi 5, Raspberry Pi OS 32-bit, 32-bit Python 3, Tkinter, systemd, `pkexec`, and a fan exposed as a Linux thermal cooling device whose type contains `fan`.

Check both the OS and Python architecture:

```bash
getconf LONG_BIT
python3 -c "import struct; print(struct.calcsize('P') * 8)"
```

Both should report `32`. If either reports `64`, do not run this edition; use the Trixie 64-bit edition if you have Raspberry Pi OS Trixie.

Install and launch from the repository root:

```bash
sudo apt update
sudo apt install -y python3-tk policykit-1
python3 fan_curve_editor.py
```

In the app, click **Install / start controller** and approve the administrator prompt. It installs the daemon under `/opt/pi5-fan-curve`, creates a systemd service, enables it at startup and starts it.

Curve editing: horizontal axis is CPU temperature from 30–90°C; vertical axis is five discrete fan levels from 0–4. Drag points, click empty graph space to add, or right-click a point to remove it. At least two points are required; up to twelve are allowed. **Apply now** saves the curve. **Restore example** loads and saves the example curve.

The curve is saved at `~/.config/pi5-fan-curve/curve.json`. The daemon checks it about once per second and maps it to discrete states supported by the detected fan cooling device. Graph percentages are labels, not precise PWM percentages.

Check fan interface support:

```bash
for d in /sys/class/thermal/cooling_device*; do
  echo "$d: $(cat "$d/type" 2>/dev/null) max=$(cat "$d/max_state" 2>/dev/null)"
done
```

If no fan cooling device appears, this edition cannot control the fan through that interface on your current OS/kernel.

Service commands:

```bash
sudo systemctl status pi5-fan-curve.service
sudo journalctl -u pi5-fan-curve.service -f
sudo systemctl disable --now pi5-fan-curve.service
```

## Trixie Edition — 64-bit Fan Curve Studio

Use this edition on Raspberry Pi OS 64-bit Trixie on Raspberry Pi 5.

- [Trixie Edition folder](trixie/)
- [Trixie Edition instructions](trixie/README.md)
- [Trixie GUI source](trixie/pi5_fan_curve_trixie.py)

From the repository root, install and launch:

```bash
sudo apt update
sudo apt install -y python3-tk
cd trixie
python3 pi5_fan_curve_trixie.py
```

The app requires 64-bit Python and checks this when it starts. It shows CPU temperature, fan RPM if exposed by the driver, the OS name, a curve preview and four editable temperature/PWM/hysteresis stages.

Click **Apply to boot config**, approve the administrator prompt and wait for the success message. The app backs up the boot config and writes the Pi 5 firmware's native fan settings. Reboot the Pi to activate the new curve. This edition does not install a background service; the Pi firmware controls the fan after reboot.

## Updating your local copy

```bash
cd pi5-fan-curve.
git pull
```

This updates the files in the cloned folder. It does not automatically reinstall a service, apply a fan curve or change the active boot configuration. Follow the instructions for your edition after updating.

## Safety and testing

- Confirm the fan is connected to the supported Pi 5 fan connector.
- Do not set fan speeds too low for your workload.
- Monitor CPU temperature under sustained load after changing settings.
- Missing fan RPM telemetry does not necessarily mean firmware fan control is unavailable.
- The original edition needs a detectable Linux fan cooling device. The Trixie edition needs the supported Pi 5 firmware fan parameters.

GitHub Actions now compiles both editions and runs unit tests for the original controller on every push and pull request. These automated checks do not prove hardware compatibility: neither edition has been verified on the owner's physical Pi, fan, and exact OS/kernel/firmware combination. Hardware behavior must still be tested on the target machine.

## References

- [Raspberry Pi OS downloads and release information](https://www.raspberrypi.com/software/operating-systems/)
- [Raspberry Pi computer documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Raspberry Pi firmware overlay parameter reference](https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README)