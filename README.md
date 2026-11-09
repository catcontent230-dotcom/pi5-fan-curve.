# Raspberry Pi 5 Fan Curve Editor

A small desktop project for configuring the fan connected to the **official four-pin fan connector on a Raspberry Pi 5**.

There are two separate editions in this repository. Choose the one that matches your Raspberry Pi OS installation. The editions use different control methods and should not be mixed.

## Start here — which edition should I use?

| Edition | Intended system | How it controls the fan | Reboot? |
|---|---|---|---|
| **Trixie Edition** (recommended for Raspberry Pi OS Trixie) | Raspberry Pi 5, Raspberry Pi OS 64-bit based on Debian 13 Trixie | Writes the Pi 5 firmware fan-curve settings in the boot configuration | Yes |
| **Original Edition** | Raspberry Pi 5 systems where Linux exposes the fan as a thermal cooling device | Background systemd service reads the saved curve and writes cooling-device states | No, normally |

**If you installed the current Raspberry Pi OS Trixie release, start with the Trixie Edition.** It uses the Pi 5 firmware's native fan-curve parameters. The original edition is retained for systems that expose a compatible `cooling_device` fan interface.

This project is for the Pi 5's supported fan interface. It is not a general-purpose GPIO fan controller and is not intended for arbitrary third-party fan wiring.

## Get the files

The repository is public:

- **[Open the GitHub repository](https://github.com/catcontent230-dotcom/pi5-fan-curve.)**
- **[Open the Trixie Edition folder](https://github.com/catcontent230-dotcom/pi5-fan-curve./tree/main/trixie)**

On your Raspberry Pi, open Terminal and clone the project:

```bash
git clone https://github.com/catcontent230-dotcom/pi5-fan-curve..git
cd pi5-fan-curve.
```

The clone command downloads the project files. It does not install or start either fan controller.

The repository name includes a full stop at the end (`pi5-fan-curve.`). Keep that full stop in the clone URL and folder name.

---

## Trixie Edition — Pi 5 Fan Curve Studio

**Use this edition for Raspberry Pi OS 64-bit Trixie.**

- [Trixie Edition instructions](trixie/README.md)
- [Trixie Edition Python application](trixie/pi5_fan_curve_trixie.py)

### Install and launch

After cloning the repository:

```bash
sudo apt update
sudo apt install -y python3-tk
cd pi5-fan-curve./trixie
python3 pi5_fan_curve_trixie.py
```

If you are already inside the cloned repository folder, just run:

```bash
sudo apt install -y python3-tk
cd trixie
python3 pi5_fan_curve_trixie.py
```

### What it does

- Shows CPU temperature, fan RPM when the system exposes it, and the detected OS name.
- Provides a visual fan-curve preview.
- Lets you edit four temperature stages, PWM values (0–255), and hysteresis.
- Checks that stage temperatures increase and fan speeds do not decrease.
- Backs up the boot configuration before changing it.
- Writes the Pi 5 firmware's native fan settings to `/boot/firmware/config.txt` (or `/boot/config.txt` if that is the existing file).

Choose **Apply to boot config** in the app and approve the administrator prompt. **Restart the Pi** to activate the new firmware settings. Merely opening the app or editing values does not change the active fan curve.

The app does not install a background service. Fan control is handled by the Pi firmware after reboot.

See [trixie/README.md](trixie/README.md) for the detailed settings, backup, validation, and safety notes.

---

## Original Edition — graph editor and background service

The original edition is kept for compatible systems where the fan appears under `/sys/class/thermal/cooling_device*` and its `type` contains the word `fan`.

### Requirements

- Raspberry Pi 5 and a compatible fan exposed as a Linux thermal cooling device
- Python 3
- Tkinter
- systemd
- `pkexec` for the GUI's administrator prompt

Install Tkinter if needed:

```bash
sudo apt update
sudo apt install -y python3-tk
```

### Launch

From the repository's top-level folder:

```bash
python3 fan_curve_editor.py
```

In the app, choose **Install / start controller** and approve the administrator prompt. The app copies the controller files into `/opt/pi5-fan-curve`, creates a systemd service, enables it at startup, and starts it.

### Editing the curve

- Horizontal axis: CPU temperature from 30°C to 90°C.
- Vertical axis: five discrete fan levels from 0 to 4.
- Drag a point to move it.
- Click an empty part of the graph to add a point.
- Select a point and choose **Remove selected**, or right-click a point, to remove it.
- At least two points are required; up to twelve are allowed.
- **Apply now** saves the curve.
- **Restore example** loads the example curve and saves it.

The curve is stored at:

```text
~/.config/pi5-fan-curve/curve.json
```

The service checks the saved curve approximately once per second. The original edition maps the curve to the discrete states reported by the detected cooling device; the displayed level percentages are labels, not precise PWM percentages.

### Check whether the original edition can see the fan

Run:

```bash
for d in /sys/class/thermal/cooling_device*; do
  echo "$d: $(cat "$d/type" 2>/dev/null) max=$(cat "$d/max_state" 2>/dev/null)"
done
```

If no device with a fan type is listed, the original edition cannot control the fan through this interface on that OS/kernel. Use the Trixie Edition on a supported Trixie Pi 5 setup instead.

### Original service commands

Check service status:

```bash
sudo systemctl status pi5-fan-curve.service
```

View live service logs:

```bash
sudo journalctl -u pi5-fan-curve.service -f
```

Stop and disable the service:

```bash
sudo systemctl disable --now pi5-fan-curve.service
```

The original daemon attempts to request full fan state when it receives a normal stop signal. Do not assume this fallback works if the driver is unavailable or the system loses power.

---

## Updating the downloaded files

To download later changes, open Terminal and run:

```bash
cd pi5-fan-curve.
git pull
```

This updates the files in the cloned folder. It does not automatically install a new service version, apply a new curve, or change the active boot configuration. Follow the relevant edition's instructions after updating.

## Safety and troubleshooting

- Check that your fan is physically connected to the Pi 5's supported fan connector.
- Do not set fan speeds too low for your workload or cooling setup.
- Monitor CPU temperature after changing fan settings, especially during sustained heavy use.
- If temperature or RPM reads as unavailable, the corresponding sensor may not be exposed by the installed kernel/driver. Missing RPM telemetry alone does not prove fan control is unavailable.
- If the GUI cannot open, check that Tkinter is installed with `sudo apt install python3-tk`.
- If an administrator prompt does not appear, the app may not be able to use `pkexec` in your desktop session.
- If the fan does not respond, check the edition-specific instructions and verify that the selected control interface exists on your system.

## Testing status

The source files have been syntax-checked, but the project has **not** been tested on the owner's physical Raspberry Pi, fan, or exact OS/kernel combination. Hardware support and behavior must be confirmed on the target Pi. Firmware, kernel, boot configuration, and fan hardware can affect the result.

## References

- [Raspberry Pi OS downloads and release information](https://www.raspberrypi.com/software/operating-systems/)
- [Raspberry Pi computer documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Raspberry Pi firmware overlay parameter reference](https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README)
