#!/usr/bin/env python3
"""32-bit system service: apply the saved fan curve once per second."""
import json, time, signal, struct
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
    candidates=[]
    try:
        candidates.extend(p/".config/pi5-fan-curve/curve.json" for p in sorted(Path("/home").iterdir()) if p.is_dir())
    except OSError:
        pass
    candidates.append(Path("/root/.config/pi5-fan-curve/curve.json"))
    return next((p for p in candidates if p.is_file()),None)

def temperature():
    try:return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text())/1000
    except Exception:return None

def interpolate(points,temp):
    if not isinstance(points,list) or not 2 <= len(points) <= 12:
        raise ValueError("Curve must contain 2–12 points")
    clean=[]
    for point in points:
        x=float(point["temp"]); level=int(point["level"])
        if not 30 <= x <= 90 or not 0 <= level <= 4:
            raise ValueError("Curve point is outside the supported range")
        clean.append({"temp":x,"level":level})
    points=sorted(clean,key=lambda p:p["temp"])
    if any(b["temp"]-a["temp"] < 2 for a,b in zip(points,points[1:])):
        raise ValueError("Curve temperatures must be at least 2°C apart")
    if temp<=points[0]["temp"]:return points[0]["level"]
    if temp>=points[-1]["temp"]:return points[-1]["level"]
    for a,b in zip(points,points[1:]):
        x,y=a["temp"],b["temp"]
        if x<=temp<=y:
            f=(temp-x)/(y-x)
            return int(a["level"]+(b["level"]-a["level"])*f+0.5)
    raise ValueError("Temperature could not be interpolated")

def main():
    if struct.calcsize("P") * 8 != 32:
        print("This controller requires 32-bit Python. Use the Trixie 64-bit edition on a 64-bit OS.", flush=True)
        return
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
                    state=int(interpolate(points,temp)/4*maximum+0.5)
                    if state!=last:
                        (fan/"cur_state").write_text(str(state)); last=state
                        print(f"{temp:.1f}°C -> state {state}/{maximum}",flush=True)
        except Exception as e:print(f"Controller warning: {e}",flush=True)
        time.sleep(1)
    try:(fan/"cur_state").write_text(str(maximum))
    except Exception:pass

if __name__=="__main__":main()
