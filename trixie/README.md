# Pi 5 Fan Curve Studio — Trixie Edition

A desktop application for configuring the fan curve on a **Raspberry Pi 5 using the official four-pin fan connector**. This is the newer, separate edition of the project. It does not replace or install the original edition.

## Is this the right edition?

Use this edition for Raspberry Pi OS 64-bit based on Debian 13 Trixie on a Raspberry Pi 5.

It uses the Pi 5 firmware's native fan-curve parameters in the boot configuration. It does **not** run the original edition's polling daemon and does not write to `/sys/class/thermal/cooling_device*/cur_state`.

This is not a generic GPIO fan controller. Do not assume it supports third-party fan wiring or other Raspberry Pi models.

## Get the project

The full project is available at:

https://github.com/catcontent230-dotcom/pi5-fan-curve.

If you have not cloned it yet, run these commands in a terminal:

```bash
git clone https://github.com/catcontent230-dotcom/pi5-fan-curve..git
cd pi5-fan-curve.
```

The repository name ends with a full stop. The double full stop before `git` in the clone URL is intentional: one is the repository-name character and one is the normal separator before `git`.

## Install and run

From the cloned repository folder:

```bash
sudo apt update
sudo apt install -y python3-tk
cd trixie
python3 pi5_fan_curve_trixie.py
```

If the app is already open, no install wizard or service setup is needed. It is a Tkinter application launched directly with Python.

## What the app shows

- **CPU temperature:** refreshed approximately every two seconds from the thermal-zone sensor, if available.
- **Fan RPM:** shown when the kernel exposes a readable `fan1_input` sensor. It may say “Not exposed” even when firmware fan control is available.
- **Operating system:** read from `/etc/os-release`.
- **Curve preview:** a graph of the four temperature stages and their PWM values.

## Editing the curve

There are four stages. Each stage has three settings:

| Setting | Meaning | Allowed values |
|---|---|---|
| Temperature | Temperature at which the stage's fan setting applies | 35–85°C |
| Fan power (PWM) | Raw fan PWM value | 0–255 |
| Hysteresis | Temperature gap used to prevent rapid switching | 1–15°C |

The app validates the curve before applying it:

- Exactly four stages are required.
- Temperatures must be strictly increasing.
- Fan power must stay the same or increase at each hotter stage.
- All values must be within the ranges above.

The preview is not a live measurement of the fan's actual PWM output. It visualizes the values you have entered.

## Default curve

The app starts with these example/default values:

| Stage | Temperature | PWM | Hysteresis |
|---|---:|---:|---:|
| 1 | 50°C | 75/255 | 5°C |
| 2 | 60°C | 125/255 | 5°C |
| 3 | 67.5°C | 175/255 | 5°C |
| 4 | 75°C | 250/255 | 5°C |

PWM is a raw value from 0 to 255, not a percentage. **Restore defaults** loads these values into the editor only; it does not write them to the boot configuration until you choose Apply.

## Apply the curve

1. Enter the four stages and check the graph.
2. Click **Apply to boot config**.
3. Read the confirmation prompt, which identifies the boot configuration file that will be changed.
4. Approve the administrator prompt.
5. Wait for the success message.
6. Reboot the Raspberry Pi to activate the firmware settings.

The app selects `/boot/firmware/config.txt` if it exists. Otherwise it uses `/boot/config.txt`.

Before the first successful edit, the app keeps a backup alongside the config file. For example, if it edits `/boot/firmware/config.txt`, the backup is `/boot/firmware/config.pi5-fan-backup`. An existing backup is not overwritten by later applies.

The app writes a clearly marked block containing `dtparam=cooling_fan=on` and the four `fan_tempN`, `fan_tempN_hyst`, and `fan_tempN_speed` settings. It removes existing active occurrences of those managed parameters from `dtparam=` lines before adding its block, while retaining unrelated entries on those lines.

**Important:** Applying changes the boot configuration, not the currently running firmware state. The new curve is not active until the Pi has rebooted.

## Undo or restore previous settings

The original boot configuration backup is kept next to the edited file. To restore it, use a terminal and copy the backup back over the active config file. For the common Trixie path:

```bash
sudo cp /boot/firmware/config.pi5-fan-backup /boot/firmware/config.txt
sudo reboot
```

If your app edited `/boot/config.txt` instead, use the matching backup and config paths under `/boot`.

Do not delete the backup until you are happy with the fan behavior.

## Troubleshooting

- **Tkinter missing:** run `sudo apt install python3-tk`.
- **No CPU temperature:** the expected thermal-zone sensor may not be exposed; check `/sys/class/thermal/thermal_zone0/temp`.
- **Fan RPM says “Not exposed”:** the kernel may not provide an RPM sensor. This alone does not mean firmware fan control is unavailable.
- **Administrator prompt fails or does not appear:** the app uses `pkexec` to request permission. Check that PolicyKit authentication works in your desktop session.
- **No change after applying:** reboot; firmware fan-curve settings are read during boot.
- **Fan does not behave as expected after reboot:** check the selected boot config, fan connection, firmware/kernel support, and any other boot settings that may affect the fan.

## Safety and testing

This application is specifically intended for the Raspberry Pi 5 supported fan interface. Keep adequate cooling for your workload. Do not use a very low curve without monitoring temperatures under sustained load.

The code has been syntax-checked, but it has **not** been tested on the owner's physical Pi, fan, or exact firmware/kernel combination. The application cannot guarantee that every OS image or firmware revision will accept or prioritize these settings. Monitor temperatures after applying the curve.

## References

- [Raspberry Pi OS downloads and release information](https://www.raspberrypi.com/software/operating-systems/)
- [Raspberry Pi computer documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Official Raspberry Pi firmware overlay parameter reference](https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README)
