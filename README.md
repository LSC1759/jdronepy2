JDrone Py
=========

FPV keyboard demo is in `fpvmode.py`.

New: GUI FPV mode in `ui_fpvmode.py` using PyQt5 with a live video preview and on-screen controls for yaw/ascent/roll/pitch, plus buttons for enable/disable, takeoff, and land. Keyboard shortcuts also work: A/D (yaw), W/S (ascent), arrows (roll/pitch), F (takeoff), R (land), E (enable), Q (disable).

Run
---

Prereqs are listed in `requirements.txt` (PyQt5, numpy, opencv-python, av, keyboard).

Windows PowerShell example:

```
python -m pip install -r requirements.txt
python ui_fpvmode.py
```

In the app:
- Enter your drone IP (default: 192.168.0.247)
- Connect, then Enable Control before moving
- Use sliders and/or keyboard controls
- Use Disable Control and Disconnect before closing

