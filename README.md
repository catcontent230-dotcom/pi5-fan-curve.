# Pi 5 Fan Curve Editor

A small Tkinter app for editing a Raspberry Pi 5 fan curve with draggable graph points, plus a systemd service that applies changes live (no reboot).

## Get the files

Open the [GitHub repository](https://github.com/catcontent230-dotcom/pi5-fan-curve.) or clone it directly onto your Raspberry Pi with:

```bash
git clone https://github.com/catcontent230-dotcom/pi5-fan-curve..git
cd pi5-fan-curve.
```

Then continue with the installation steps below. This gets a copy of the project onto your Pi; it does not install or start the fan controller by itself.

## Trixie Edition (new GUI)

A redesigned interface specifically for Raspberry Pi OS 64-bit Trixie on Pi 5. It uses the Pi 5 firmware's native fan-curve parameters instead of the original polling daemon.

- [Open the Trixie edition folder](https://github.com/catcontent230-dotcom/pi5-fan-curve./tree/main/trixie)
- [Trixie edition instructions](https://github.com/catcontent230-dotcom/pi5-fan-curve./blob/main/trixie/README.md)
- [Download the Trixie GUI](https://github.com/catcontent230-dotcom/pi5-fan-curve./blob/main/trixie/pi5_fan_curve_trixie.py)

Run it on the Pi with:

```bash
sudo apt update
sudo apt install -y python3-tk
cd trixie
python3 pi5_fan_curve_trixie.py
```

The Trixie app edits `/boot/firmware/config.txt` and requires a reboot for firmware settings to take effect. It is a separate version; the original files below are unchanged.

## Requirements
- Raspberry Pi 5 with Raspberry Pi OS 64-bit
- Python 3, Tkinter, systemd
- A fan exposed as a Linux thermal cooling device whose `type` contains `fan`

Install Tkinter if needed:
```bash
sudo apt update
sudo apt install -y python3-tk
```

## Install
```bash
git clone https://github.com/catcontent230-dotcom/pi5-fan-curve..git
cd pi5-fan-curve.
python3 fan_curve_editor.py
```
In the app, choose **Install / start controller** and approve the administrator prompt. Then edit the curve; changes are saved and the service reads them within about one second.

## Graph
- X axis: CPU temperature, 30–90°C
- Y axis: five fan levels (0–4)
- Drag a point to move it
- Click empty graph space to add a point
- Right-click a point to remove it
- **Apply now** saves the curve immediately

The Pi 5 interface exposes discrete cooling states, not arbitrary PWM percentages. The percentages shown are approximate labels for those five levels.

## Check hardware support
```bash
for d in /sys/class/thermal/cooling_device*; do
  echo "$d: $(cat "$d/type" 2>/dev/null) max=$(cat "$d/max_state" 2>/dev/null)"
done
```
If no fan cooling device appears, this controller cannot operate through that interface on your current OS/kernel.

## Service
```bash
sudo systemctl status pi5-fan-curve.service
sudo journalctl -u pi5-fan-curve.service -f
sudo systemctl disable --now pi5-fan-curve.service
```

**Note:** This has not been verified on your specific Pi/kernel. Some firmware or thermal governors may override manual cooling-device writes. Monitor temperatures after installing.
