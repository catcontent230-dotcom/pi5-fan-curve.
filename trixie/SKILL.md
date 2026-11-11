# Gui Fan Editor

A 64-bit Python GUI fan curve editor for Raspberry Pi 5 with scatter graph and editable points.

## Features

- **64-bit only** — requires 64-bit Python (unlike the 32-bit Original edition)
- **Scatter graph** — temperature (°C) on horizontal axis, fan level (0–4) on vertical axis
- **Editable dots** — click to add points, drag to move, right-click to delete
- **Point validation** — 2–12 points, temperatures 30–90°C, at least 2°C apart, levels 0–4
- **Apply saved curve** — writes to `~/.config/pi5-fan-curve/curve.json`
- **Install controller** — installs systemd service with administrator permission
- **Refresh telemetry** — shows current CPU temperature and fan device status

## Screenshot

![Pi 5 Fan Curve Editor - 64-bit edition](https://github.com/catcontent230-dotcom/pi5-fan-curve/raw/main/fan_curve_editor.py)

## Installation

```bash
# Clone this skill or copy the gui-fan-editor directory
git clone https://github.com/yourusername/gui-fan-editor.git

# Run the editor
python3 gui-fan-editor/gui_fan_editor.py
```

## Usage

1. Launch the editor — it will auto-detect 64-bit Python
2. Click empty graph space to add points, or drag existing points to adjust
   - Right-click any point to delete it (minimum 2 points required)
3. Use "Add point" button or click empty space to add new points
4. Use "Remove selected" to delete the currently selected point
5. Click "Apply now" to save the curve to `~/.config/pi5-fan-curve/curve.json`
6. Use "Install / start controller" to install the systemd service (admin required)

## Configuration

The edited curve is saved at `~/.config/pi5-fan-curve/curve.json` and can be used by the Pi 5 fan daemon/controller.

## Requirements

- Raspberry Pi 5
- Raspberry Pi OS 64-bit (Trixie or newer)
- 64-bit Python 3
- Tkinter (`sudo apt install -y python3-tk`)
- A fan connected to the supported Pi 5 fan connector

## License

MIT