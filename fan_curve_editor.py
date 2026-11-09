#!/usr/bin/env python3
"""Raspberry Pi 5 fan curve graph editor — 32-bit edition."""
import json, subprocess, time, struct
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

CONFIG = Path.home() / ".config/pi5-fan-curve/curve.json"
APP_DIR = Path("/opt/pi5-fan-curve")
DEFAULT = [{"temp":40,"level":0},{"temp":50,"level":1},{"temp":60,"level":2},{"temp":67,"level":3},{"temp":75,"level":4}]

def load_curve():
    try:
        pts=json.loads(CONFIG.read_text()).get("points", DEFAULT)
        if len(pts)>=2: return sorted([{"temp":float(p["temp"]),"level":int(p["level"])} for p in pts],key=lambda p:p["temp"])
    except Exception: pass
    return [p.copy() for p in DEFAULT]

def save_curve(points):
    CONFIG.parent.mkdir(parents=True,exist_ok=True)
    tmp=CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps({"points":sorted(points,key=lambda p:p["temp"]),"updated":time.time()},indent=2))
    tmp.replace(CONFIG)

def fan_device():
    for d in Path("/sys/class/thermal").glob("cooling_device*"):
        try:
            if "fan" in (d/"type").read_text().strip().lower(): return d
        except Exception: pass
    return None

def cpu_temp():
    try: return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text())/1000
    except Exception: return None

class App:
    def __init__(self,root):
        self.root=root; root.title("Pi 5 Fan Curve Editor"); root.geometry("900x650"); root.minsize(700,520)
        self.points=load_curve(); self.selected=None; self.drag=False
        self.status=tk.StringVar(value="Ready"); self.stats=tk.StringVar(value="Reading hardware…")
        outer=ttk.Frame(root,padding=14); outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="Fan curve",font=("TkDefaultFont",20,"bold")).pack(anchor="w")
        ttk.Label(outer,textvariable=self.stats).pack(anchor="w",pady=8)
        self.canvas=tk.Canvas(outer,bg="#171923",highlightthickness=0); self.canvas.pack(fill="both",expand=True)
        self.canvas.bind("<Configure>",lambda e:self.draw()); self.canvas.bind("<Button-1>",self.click)
        self.canvas.bind("<B1-Motion>",self.move); self.canvas.bind("<ButtonRelease-1>",self.release)
        self.canvas.bind("<Button-3>",self.delete_at)
        bar=ttk.Frame(outer); bar.pack(fill="x",pady=10)
        for label,cmd in [("Add point",self.add),("Remove selected",self.remove),("Apply now",self.apply),("Restore example",self.restore)]:
            ttk.Button(bar,text=label,command=cmd).pack(side="left",padx=(0,6))
        ttk.Button(bar,text="Install / start controller",command=self.install).pack(side="right")
        ttk.Label(outer,text="Drag points · click empty space to add · right-click a point to delete").pack(anchor="w")
        ttk.Label(outer,text="Levels: 0 Off · 1 Low · 2 Medium · 3 High · 4 Full (discrete hardware states)").pack(anchor="w")
        ttk.Label(outer,textvariable=self.status).pack(anchor="w",pady=6)
        self.draw(); self.refresh()

    def bounds(self):
        w,h=self.canvas.winfo_width(),self.canvas.winfo_height()
        return 58,w-24,24,h-48
    def xy(self,p):
        l,r,t,b=self.bounds()
        return l+(p["temp"]-30)/60*(r-l), b-p["level"]/4*(b-t)
    def data(self,x,y):
        l,r,t,b=self.bounds()
        return max(30,min(90,30+(x-l)/(r-l)*60)),max(0,min(4,round((b-y)/(b-t)*4)))
    def draw(self):
        if not hasattr(self,"canvas"): return
        c=self.canvas; c.delete("all"); l,r,t,b=self.bounds()
        if r-l<100:return
        for n in range(5):
            y=b-n/4*(b-t); c.create_line(l,y,r,y,fill="#343847",dash=(3,4))
            c.create_text(l-10,y,text=f"{n*25}%",fill="#ddd",anchor="e")
        for temp in range(30,91,10):
            x=l+(temp-30)/60*(r-l); c.create_line(x,t,x,b,fill="#292e3c")
            c.create_text(x,b+16,text=str(temp),fill="#ddd")
        c.create_text((l+r)/2,self.canvas.winfo_height()-10,text="CPU temperature (°C)",fill="white")
        pts=sorted(self.points,key=lambda p:p["temp"]); coords=[self.xy(p) for p in pts]
        if len(coords)>1:
            for a,z in zip(coords,coords[1:]): c.create_line(*a,*z,fill="#a78bfa",width=3)
        for p,(x,y) in zip(pts,coords):
            sel=p is self.selected; rad=9 if sel else 6
            c.create_oval(x-rad,y-rad,x+rad,y+rad,fill="#f0abfc" if sel else "#a78bfa",outline="white",width=2)
            c.create_text(x,y-17,text=f'{p["temp"]:.0f}° / {p["level"]*25}%',fill="white")
    def nearest(self,x,y):
        found=[( ((self.xy(p)[0]-x)**2+(self.xy(p)[1]-y)**2)**.5,p) for p in self.points]
        found=[v for v in found if v[0]<19]
        return min(found,key=lambda v:v[0])[1] if found else None
    def click(self,e):
        p=self.nearest(e.x,e.y)
        if p:self.selected=p; self.drag=True; self.draw()
        else:
            temp,level=self.data(e.x,e.y); self.insert(temp,level)
    def move(self,e):
        if not self.drag or not self.selected:return
        temp,level=self.data(e.x,e.y); pts=sorted(self.points,key=lambda p:p["temp"]); i=pts.index(self.selected)
        lo=30 if i==0 else pts[i-1]["temp"]+1; hi=90 if i==len(pts)-1 else pts[i+1]["temp"]-1
        self.selected["temp"]=round(max(lo,min(hi,temp)),1); self.selected["level"]=level; self.draw()
    def release(self,e):
        if self.drag:self.drag=False; self.apply()
    def delete_at(self,e):
        p=self.nearest(e.x,e.y)
        if p and len(self.points)>2:self.points.remove(p); self.selected=None; self.apply()
    def insert(self,temp,level):
        if len(self.points)>=12:self.status.set("Maximum 12 points"); return
        if any(abs(p["temp"]-temp)<2 for p in self.points):self.status.set("Points must be 2°C apart"); return
        self.points.append({"temp":round(temp,1),"level":level}); self.selected=self.points[-1]; self.apply()
    def add(self):
        for temp in range(35,90,5):
            if all(abs(temp-p["temp"])>=2 for p in self.points):self.insert(temp,2); return
        self.status.set("No room for another point")
    def remove(self):
        if self.selected and len(self.points)>2:self.points.remove(self.selected); self.selected=None; self.apply()
        else:self.status.set("Select a point; at least two are required")
    def apply(self):
        self.points.sort(key=lambda p:p["temp"]); save_curve(self.points); self.draw()
        self.status.set("Saved. The background controller reloads changes within about one second.")
    def restore(self):
        if messagebox.askyesno("Restore","Restore the example fan curve?"):
            self.points=[p.copy() for p in DEFAULT]; self.selected=None; self.apply()
    def refresh(self):
        temp=cpu_temp(); d=fan_device()
        state="Fan interface not detected"
        if d:
            try: state=f'Fan state: {(d/"cur_state").read_text().strip()}/{(d/"max_state").read_text().strip()}'
            except Exception: state=f"Fan device: {d}"
        self.stats.set((f"CPU: {temp:.1f}°C · " if temp is not None else "CPU unavailable · ")+state)
        self.root.after(1500,self.refresh)
    def install(self):
        if not messagebox.askyesno("Install controller","Install and start the system service? Administrator permission is required."):return
        script=Path(__file__).resolve()
        cmd=("mkdir -p /opt/pi5-fan-curve && cp '"+str(script)+"' /opt/pi5-fan-curve/fan_curve_editor.py && cp '"+str(script.parent/"fan_daemon.py")+"' /opt/pi5-fan-curve/fan_daemon.py && chmod 755 /opt/pi5-fan-curve/*.py && "
             "printf '[Unit]\\nDescription=Pi 5 Fan Curve Controller\\nAfter=multi-user.target\\n\\n[Service]\\nType=simple\\nExecStart=/usr/bin/python3 /opt/pi5-fan-curve/fan_daemon.py\\nRestart=always\\nRestartSec=2\\n\\n[Install]\\nWantedBy=multi-user.target\\n' > /etc/systemd/system/pi5-fan-curve.service && systemctl daemon-reload && systemctl enable --now pi5-fan-curve.service")
        try:subprocess.run(["pkexec","/bin/sh","-c",cmd],check=True); messagebox.showinfo("Installed","Controller installed and started.")
        except Exception as e:messagebox.showerror("Install failed",str(e))

if __name__=="__main__":
    root=tk.Tk()
    if struct.calcsize("P") * 8 != 32:
        messagebox.showerror("32-bit edition only", "This original edition requires 32-bit Python. Use the Trixie Edition for 64-bit Raspberry Pi OS.")
        root.destroy()
    else:
        App(root); root.mainloop()
