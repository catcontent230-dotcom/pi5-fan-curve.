# Pi 5 Fan Curve Studio — Trixie 64-bit Edition

A desktop application for configuring the fan curve on a Raspberry Pi 5 running Raspberry Pi OS 64-bit Trixie, using the official four-pin fan connector.

**Architecture requirement: 64-bit OS and 64-bit Python.** The application checks the Python runtime and refuses to start under 32-bit Python. Use the Original 32-bit Edition in the repository root for a 32-bit OS instead.

## Check your system

```bash
getconf LONG_BIT
python3 -c "import struct; print(struct.calcsize('P') * 8)"
cat /etc/os-release
```

Both architecture checks should report `64`, and the OS should identify Raspberry Pi OS based on Debian Trixie.

## Get and run the project

If you have not cloned the repository yet:

```bash
git clone https://github.com/catcontent230-dotcom/pi5-fan-curve..git
cd pi5-fan-curve.
```

Then install Tkinter and launch the app:

```bash
sudo apt update
sudo apt install -y python3-tk
cd trixie
python3 pi5_fan_curve_trixie.py
```

If you are already inside the repository's `trixie` folder, run only `python3 pi5_fan_curve_trixie.py`.

## How this edition works

This edition uses the Raspberry Pi 5 firmware's native fan-curve parameters in the boot configuration. It does not run the original edition's polling daemon and does not write to `/sys/class/thermal/cooling_device*/cur_state`. It is not a generic GPIO fan controller and is not intended for other Pi models or arbitrary third-party fan wiring.

## What the app shows

- CPU temperature, refreshed approximately every two seconds when the thermal-zone sensor is available.
- Fan RPM when the kernel exposes a readable `fan1_input` sensor. “Not exposed” does not by itself mean fan control is unavailable.
- Operating system name, read from `/etc/os-release`.
- A curve preview of the four temperature stages and PWM values.

## Editing the curve

There are four stages. Each stage has three settings:

| Setting | Meaning | Allowed values |
|---|---|---|
| Temperature | Temperature threshold for the stage | 35–85°C |
| Fan power (PWM) | Raw fan PWM value | 0–255 |
| Hysteresis | Temperature gap used to prevent rapid switching | 1–15°C |

The app requires exactly four stages, strictly increasing temperatures, and fan power that stays the same or increases at hotter stages. The preview shows the values entered; it is not a live measurement of actual fan PWM.

## Default curve

| Stage | Temperature | PWM | Hysteresis |
|---|---:|---:|---:|
| 1 | 50°C | 75/255 | 5°C |
| 2 | 60°C | 125/255 | 5°C |
| 3 | 67.5°C | 175/255 | 5°C |
| 4 | 75°C | 250/255 | 5°C |

PWM is a raw value from 0 to 255, not a percentage. **Restore defaults** only changes the values in the editor until you apply them.

## Apply the curve

1. Edit the four stages and check the preview.
2. Click **Apply to boot config**.
3. Check the confirmation prompt showing the file that will be changed.
4. Approve the administrator prompt.
5. Wait for the success message.
6. Reboot the Pi. The new firmware curve is not active until after reboot.

The app uses `/boot/firmware/config.txt` if it exists, otherwise `/boot/config.txt`. Before the first successful edit it creates a backup alongside that file. For the usual Trixie path, the backup is `/boot/firmware/config.pi5-fan-backup`. An existing backup is not overwritten by later applies.

The app writes a marked block with `dtparam=cooling_fan=on` and the four `fan_tempN`, `fan_tempN_hyst`, and `fan_tempN_speed` parameters. It removes existing active occurrences of these managed parameters from `dtparam=` lines while retaining unrelated entries on those lines.

## Restore the previous boot configuration

For the usual Trixie path:

```bash
sudo cp /boot/firmware/config.pi5-fan-backup /boot/firmware/config.txt
sudo reboot
```

If the app edited `/boot/config.txt`, use the matching backup and config paths under `/boot`. Keep the backup until you are satisfied with the fan behavior.

## Troubleshooting

- 32-bit edition warning: check that both architecture commands above report `64`. A 32-bit OS should use the Original Edition.
- Tkinter missing: `sudo apt install python3-tk`.
- No CPU temperature: check `/sys/class/thermal/thermal_zone0/temp`.
- Fan RPM unavailable: the kernel may not expose an RPM sensor; fan firmware control may still work.
- Administrator prompt fails: the app uses `pkexec`; check PolicyKit authentication in your desktop session.
- No change after applying: reboot; firmware settings are read during boot.
- Unexpected fan behavior: check the boot config, fan connection, and firmware/kernel support.

## Safety and testing

Keep adequate cooling for your workload and monitor CPU temperature under sustained load. This application is specifically intended for the supported Raspberry Pi 5 fan interface.

The source has been syntax-checked but has not been tested on the owner's physical Pi, fan, or exact firmware/kernel combination. The app cannot guarantee every OS image or firmware revision will accept or prioritize these settings.

## References

- [Raspberry Pi OS downloads and release information](https://www.raspberrypi.com/software/operating-systems/)
- [Raspberry Pi computer documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Official Raspberry Pi firmware overlay parameter reference](https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README)