#!/usr/bin/env python3
"""System service: apply the saved fan curve once per second."""
import json, time, signal
from pathlib import Path

THERMAL=Path("/sys/class/thermal")
running=True

def stop(*_):
    global running
    running=False
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)

def find_fan():
    for d in THERMAL.glob("cooling_device*"):
        try:
            if "fan" in (d/"type").read_text().strip().lower(): return d
        except Exception: pass
    return None

def find_config():
    candidates=[p/".config/pi5-fan-curve/curve.json" for p in Path("/home").iterdir() if p.is_dir()]
    candidates.append(Path("/root/.config/pi5-fan-curve/curve.json"))
    return next((p for p in candidates if p.exists()),None)

def temperature():
    try:return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text())/1000
    except Exception:return None

def interpolate(points,temp):
    points=sorted(points,key=lambda p:float(p["temp"]))
    if temp<=float(points[0]["temp"]):return int(points[0]["level"])
    if temp>=float(points[-1]["temp"]):return int(points[-1]["level"])
    for a,b in zip(points,points[1:]):
        x,y=float(a["temp"]),float(b["temp"])
        if x<=temp<=y:
            f=(temp-x)/(y-x)
            return round(int(a["level"])+(int(b["level"])-int(a["level"]))*f)
    return 4

def main():
    fan=find_fan()
    if fan is None:
        print("No fan cooling device found; check the Pi fan driver.",flush=True); return
    maximum=int((fan/"max_state").read_text()); last=None
    print(f"Controlling {fan}; max_state={maximum}",flush=True)
    while running:
        try:
            cfg=find_config(); temp=temperature()
            if cfg and temp is not None:
                points=json.loads(cfg.read_text()).get("points",[])
                if len(points)>=2:
                    state=round(interpolate(points,temp)/4*maximum)
                    if state!=last:
                        (fan/"cur_state").write_text(str(state)); last=state
                        print(f"{temp:.1f}°C -> state {state}/{maximum}",flush=True)
        except Exception as e:print(f"Controller warning: {e}",flush=True)
        time.sleep(1)
    try:(fan/"cur_state").write_text(str(maximum))
    except Exception:pass

if __name__=="__main__":main()
