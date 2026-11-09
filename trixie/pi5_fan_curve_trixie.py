#!/usr/bin/env python3
"""Pi 5 Fan Curve Studio — Raspberry Pi OS Trixie edition.
Uses the Pi 5 firmware's native fan_tempN config.txt parameters.
"""
from __future__ import annotations
import os, platform, re, shutil, subprocess, tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

APP = "Pi 5 Fan Curve Studio"
CONFIG_CANDIDATES = [Path('/boot/firmware/config.txt'), Path('/boot/config.txt')]
MANAGED_START = '# BEGIN PI5 FAN CURVE STUDIO'
MANAGED_END = '# END PI5 FAN CURVE STUDIO'
BG = '#0b1020'; PANEL = '#121a2d'; PANEL2 = '#18233a'; TEXT = '#eef3ff'
MUTED = '#91a0ba'; ACCENT = '#8b7cff'; CYAN = '#4dd8d0'
DEFAULTS = [
    {'temp': 50, 'speed': 75, 'hyst': 5},
    {'temp': 60, 'speed': 125, 'hyst': 5},
    {'temp': 67.5, 'speed': 175, 'hyst': 5},
    {'temp': 75, 'speed': 250, 'hyst': 5},
]

def read_temp():
    try: return int(Path('/sys/class/thermal/thermal_zone0/temp').read_text().strip()) / 1000
    except (OSError, ValueError): return None

def read_fan_rpm():
    for p in Path('/sys/class/hwmon').glob('hwmon*/fan1_input'):
        try:
            value = int(p.read_text().strip())
            if value > 0: return value
        except (OSError, ValueError): pass
    return None

def os_description():
    data = {}
    try:
        for line in Path('/etc/os-release').read_text().splitlines():
            if '=' in line:
                k, v = line.split('=', 1); data[k] = v.strip('"')
    except OSError: pass
    return data.get('PRETTY_NAME', platform.system())

def config_path():
    return next((p for p in CONFIG_CANDIDATES if p.exists()), CONFIG_CANDIDATES[0])

def make_block(points):
    lines = [MANAGED_START, '# Managed by Pi 5 Fan Curve Studio. Edit through the app.', '[all]', 'dtparam=cooling_fan=on']
    for i, p in enumerate(points):
        temp = round(float(p['temp']) * 1000)
        hyst = round(float(p['hyst']) * 1000)
        speed = int(p['speed'])
        lines += [f'dtparam=fan_temp{i}={temp}', f'dtparam=fan_temp{i}_hyst={hyst}', f'dtparam=fan_temp{i}_speed={speed}']
    lines.append(MANAGED_END)
    return '\n'.join(lines)

def validate(points):
    if len(points) != 4: return 'Exactly four fan stages are required.'
    temps = [float(p['temp']) for p in points]
    speeds = [int(p['speed']) for p in points]
    if any(t < 35 or t > 85 for t in temps): return 'Temperatures must be between 35°C and 85°C.'
    if temps != sorted(temps) or len(set(temps)) != 4: return 'Each stage temperature must be higher than the previous one.'
    if any(s < 0 or s > 255 for s in speeds): return 'Fan PWM values must be between 0 and 255.'
    if speeds != sorted(speeds): return 'Fan speeds must stay the same or increase at higher temperatures.'
    if any(float(p['hyst']) < 1 or float(p['hyst']) > 15 for p in points): return 'Hysteresis must be between 1°C and 15°C.'
    return None

class FanCurveStudio:
    def __init__(self, root):
        self.root=root; root.title(APP); root.geometry('1120x790'); root.minsize(900,680); root.configure(bg=BG)
        self.points=[p.copy() for p in DEFAULTS]; self.vars=[]
        self._style(); self._build(); self._refresh_telemetry(); self.draw_graph()

    def _style(self):
        s=ttk.Style(); s.theme_use('clam')
        s.configure('.',background=BG,foreground=TEXT,fieldbackground=PANEL2,bordercolor=PANEL2,font=('TkDefaultFont',10))
        s.configure('TFrame',background=BG); s.configure('TLabel',background=BG,foreground=TEXT)
        s.configure('Muted.TLabel',background=BG,foreground=MUTED)
        s.configure('CardTitle.TLabel',background=PANEL,foreground=MUTED,font=('TkDefaultFont',9,'bold'))
        s.configure('Heading.TLabel',background=BG,foreground=TEXT,font=('TkDefaultFont',21,'bold'))
        s.configure('TButton',background=PANEL2,foreground=TEXT,padding=(13,9),borderwidth=0)
        s.map('TButton',background=[('active','#273654')])
        s.configure('Accent.TButton',background=ACCENT,foreground='white',font=('TkDefaultFont',10,'bold'))
        s.map('Accent.TButton',background=[('active','#a69cff')])
        s.configure('TEntry',fieldbackground=PANEL2,foreground=TEXT,insertcolor=TEXT,padding=7)

    def _build(self):
        header=tk.Frame(self.root,bg=BG); header.pack(fill='x',padx=26,pady=(22,15))
        tk.Label(header,text='FAN CURVE STUDIO',bg=BG,fg=CYAN,font=('TkDefaultFont',9,'bold')).pack(anchor='w')
        ttk.Label(header,text='Make your Pi run cooler. Or quieter.',style='Heading.TLabel').pack(anchor='w',pady=(5,2))
        ttk.Label(header,text='Native Raspberry Pi 5 fan control · Raspberry Pi OS Trixie edition',style='Muted.TLabel').pack(anchor='w')
        cards=tk.Frame(self.root,bg=BG); cards.pack(fill='x',padx=26,pady=(0,15))
        self.temp_value=tk.StringVar(value='--.-°C'); self.rpm_value=tk.StringVar(value='—'); self.os_value=tk.StringVar(value='Checking system…')
        self._metric(cards,'CPU TEMPERATURE',self.temp_value,'Live sensor reading',0)
        self._metric(cards,'FAN SPEED',self.rpm_value,'RPM, when exposed by driver',1)
        self._metric(cards,'OPERATING SYSTEM',self.os_value,'Detected from /etc/os-release',2,True)
        content=tk.Frame(self.root,bg=BG); content.pack(fill='both',expand=True,padx=26,pady=(0,15))
        left=tk.Frame(content,bg=PANEL,padx=18,pady=16); left.pack(side='left',fill='both',expand=True,padx=(0,12))
        right=tk.Frame(content,bg=PANEL,padx=18,pady=16,width=330); right.pack(side='right',fill='y'); right.pack_propagate(False)
        tk.Label(left,text='YOUR FAN CURVE',bg=PANEL,fg=TEXT,font=('TkDefaultFont',12,'bold')).pack(anchor='w')
        tk.Label(left,text='Four temperature stages · live preview of your settings',bg=PANEL,fg=MUTED).pack(anchor='w',pady=(4,10))
        self.graph=tk.Canvas(left,height=340,bg='#0e1628',highlightthickness=0); self.graph.pack(fill='both',expand=True)
        self.graph.bind('<Configure>',lambda e:self.draw_graph())
        tk.Label(left,text='The fan controller runs in firmware. Your settings take effect after a reboot.',bg=PANEL,fg=MUTED,wraplength=600,justify='left').pack(anchor='w',pady=(12,0))
        tk.Label(right,text='STAGE SETTINGS',bg=PANEL,fg=TEXT,font=('TkDefaultFont',12,'bold')).pack(anchor='w')
        tk.Label(right,text='Adjust each point in the curve',bg=PANEL,fg=MUTED).pack(anchor='w',pady=(4,12))
        for i,p in enumerate(self.points):
            card=tk.Frame(right,bg=PANEL2,padx=11,pady=9); card.pack(fill='x',pady=5)
            top=tk.Frame(card,bg=PANEL2); top.pack(fill='x')
            tk.Label(top,text=f'STAGE {i+1}',bg=PANEL2,fg=CYAN,font=('TkDefaultFont',8,'bold')).pack(side='left')
            tk.Label(top,text=f'{p["speed"]}/255 PWM',bg=PANEL2,fg=TEXT,font=('TkDefaultFont',9,'bold')).pack(side='right')
            tv=tk.StringVar(value=str(p['temp'])); sv=tk.StringVar(value=str(p['speed'])); hv=tk.StringVar(value=str(p['hyst']))
            for label,var,unit in [('Temperature',tv,'°C'),('Fan power',sv,'0–255'),('Hysteresis',hv,'°C')]:
                row=tk.Frame(card,bg=PANEL2); row.pack(fill='x',pady=(7,0))
                tk.Label(row,text=label,bg=PANEL2,fg=MUTED).pack(side='left')
                ttk.Entry(row,textvariable=var,width=6).pack(side='right')
                tk.Label(row,text=unit,bg=PANEL2,fg=MUTED).pack(side='right',padx=(0,5))
            self.vars.append((tv,sv,hv))
            for v in (tv,sv,hv): v.trace_add('write',lambda *_:self._inputs_changed())
        footer=tk.Frame(self.root,bg=BG); footer.pack(fill='x',padx=26,pady=(0,22))
        self.status=tk.StringVar(value='Ready · your current boot settings have not been changed.')
        tk.Label(footer,textvariable=self.status,bg=BG,fg=MUTED,anchor='w').pack(side='left',fill='x',expand=True)
        ttk.Button(footer,text='Restore defaults',command=self.restore).pack(side='right',padx=(8,0))
        ttk.Button(footer,text='Apply to boot config',style='Accent.TButton',command=self.apply).pack(side='right')

    def _metric(self,parent,title,value,note,col,compact=False):
        f=tk.Frame(parent,bg=PANEL,padx=16,pady=12); f.grid(row=0,column=col,sticky='nsew',padx=(0 if col==0 else 8,0))
        parent.grid_columnconfigure(col,weight=1)
        ttk.Label(f,text=title,style='CardTitle.TLabel').pack(anchor='w')
        tk.Label(f,textvariable=value,bg=PANEL,fg=TEXT,font=('TkDefaultFont',18 if compact else 23,'bold'),wraplength=300).pack(anchor='w',pady=(5,2))
        tk.Label(f,text=note,bg=PANEL,fg=MUTED,font=('TkDefaultFont',8)).pack(anchor='w')

    def _read_inputs(self):
        return [{'temp':float(tv.get()),'speed':int(sv.get()),'hyst':float(hv.get())} for tv,sv,hv in self.vars]

    def _inputs_changed(self):
        try:
            self.points=self._read_inputs(); self.draw_graph()
            self.status.set('Unsaved changes · check the curve, then apply when ready.')
        except (ValueError,tk.TclError): self.status.set('Enter valid numbers in each stage.')

    def draw_graph(self):
        if not hasattr(self,'graph'): return
        c=self.graph; c.delete('all'); w=max(c.winfo_width(),300); h=max(c.winfo_height(),220)
        l,r,t,b=54,w-22,22,h-45
        for temp in range(30,91,10):
            x=l+(temp-30)/60*(r-l); c.create_line(x,t,x,b,fill='#24314a')
            c.create_text(x,b+17,text=str(temp),fill=MUTED,font=('TkDefaultFont',8))
        for speed in (0,64,128,192,255):
            y=b-speed/255*(b-t); c.create_line(l,y,r,y,fill='#24314a',dash=(3,4))
            c.create_text(l-9,y,text=str(speed),fill=MUTED,anchor='e',font=('TkDefaultFont',8))
        c.create_text((l+r)/2,h-9,text='CPU temperature (°C)',fill=MUTED,font=('TkDefaultFont',8))
        try: pts=sorted(self.points,key=lambda p:p['temp'])
        except Exception: return
        coords=[(l+(p['temp']-30)/60*(r-l),b-p['speed']/255*(b-t)) for p in pts]
        if coords:
            allcoords=[(l,b)]+coords+[(r,coords[-1][1])]
            for a,z in zip(allcoords,allcoords[1:]): c.create_line(*a,*z,fill=ACCENT,width=3,smooth=True)
            for i,(x,y) in enumerate(coords):
                c.create_oval(x-8,y-8,x+8,y+8,fill=CYAN,outline='#eafcff',width=2)
                c.create_text(x,y-19,text=f'{pts[i]["temp"]:g}°  {pts[i]["speed"]}',fill=TEXT,font=('TkDefaultFont',8,'bold'))

    def restore(self):
        if not messagebox.askyesno('Restore defaults','Restore the official Raspberry Pi 5 default fan curve? This only changes the editor until you apply it.'): return
        self.points=[p.copy() for p in DEFAULTS]
        for p,(tv,sv,hv) in zip(self.points,self.vars): tv.set(str(p['temp'])); sv.set(str(p['speed'])); hv.set(str(p['hyst']))
        self.draw_graph(); self.status.set('Default curve loaded in the editor. Not applied yet.')

    def apply(self):
        try: points=self._read_inputs()
        except ValueError:
            messagebox.showerror('Invalid values','Please enter numbers in all stage fields.'); return
        problem=validate(points)
        if problem: messagebox.showerror('Check your curve',problem); return
        path=config_path()
        if not messagebox.askyesno('Apply fan curve',f'This will back up and edit:\n{path}\n\nThe Pi must reboot before the new curve takes effect. Continue?'): return
        cleaned=re.sub(re.escape(MANAGED_START)+r'.*?'+re.escape(MANAGED_END)+r'\s*','',path.read_text() if path.exists() else '',flags=re.S)
        kept=[]; target=re.compile(r'^(cooling_fan|fan_temp[0-3](?:_hyst|_speed)?)\s*=',re.I)
        for line in cleaned.splitlines():
            match=re.match(r'^(\s*dtparam\s*=\s*)(.*)$',line,re.I)
            if not match: kept.append(line); continue
            entries=[part.strip() for part in match.group(2).split(',')]
            remaining=[part for part in entries if not target.match(part)]
            if remaining: kept.append(match.group(1)+','.join(remaining))
        new_text='\n'.join(kept).rstrip()+'\n\n'+make_block(points)+'\n'
        staged=None
        try:
            fd,name=tempfile.mkstemp(prefix='pi5-fan-curve-',suffix='.txt'); staged=Path(name)
            with os.fdopen(fd,'w') as handle: handle.write(new_text)
            py=("import pathlib,shutil,sys; p=pathlib.Path(sys.argv[1]); src=pathlib.Path(sys.argv[2]); "
                "b=p.with_suffix(p.suffix+'.pi5-fan-backup'); shutil.copy2(p,b) if p.exists() and not b.exists() else None; "
                "shutil.copyfile(src,p); shutil.copystat(b,p) if b.exists() else None")
            proc=subprocess.run(['pkexec','python3','-c',py,str(path),str(staged)],text=True,capture_output=True,timeout=60)
            if proc.returncode: raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f'pkexec exited {proc.returncode}')
        except Exception as e:
            messagebox.showerror('Could not apply settings',f'{e}\n\nNo success was reported. You can still copy the settings manually from the README.'); return
        finally:
            if staged is not None:
                try: staged.unlink()
                except OSError: pass
        self.points=points; self.status.set(f'Applied to {path}. Reboot required to activate the new curve.')
        messagebox.showinfo('Fan curve saved',f'Your fan curve has been written to:\n{path}\n\nA backup was kept as {path.name}.pi5-fan-backup (if one did not already exist).\n\nRestart your Raspberry Pi to activate it.')

    def _refresh_telemetry(self):
        temp=read_temp(); rpm=read_fan_rpm()
        self.temp_value.set(f'{temp:.1f}°C' if temp is not None else 'Unavailable')
        self.rpm_value.set(f'{rpm:,} RPM' if rpm is not None else 'Not exposed')
        self.os_value.set(os_description())
        self.root.after(2000,self._refresh_telemetry)

if __name__=='__main__':
    root=tk.Tk(); FanCurveStudio(root); root.mainloop()
