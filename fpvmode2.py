# j drone test 1

import json
import time
import keyboard
import cv2
import numpy as np
from jdrone import OpenDJI

# ----------------------------
# CONFIGURATION
# ----------------------------
IP_ADDR = "192.168.0.247"
SCALE_FACTOR = 0.5

MOVE_VALUE = 0.015
ROTATE_VALUE = 0.15

GIMBAL_STEP_PITCH = 20
GIMBAL_STEP_YAW = 20
GIMBAL_MIN_PITCH = -90
GIMBAL_MAX_PITCH = 30
GIMBAL_MIN_YAW = -180
GIMBAL_MAX_YAW = 180

current_pitch = 0
current_yaw = 0

# Placeholder frame if no video is available
BLANK_FRAME = np.zeros((1080, 1920, 3), dtype=np.uint8)
cv2.putText(BLANK_FRAME, "No Image", (200, 300),
            cv2.FONT_HERSHEY_DUPLEX, 10, (255, 255, 255), 15)

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------
def send_gimbal(drone, pitch: float, yaw: float):
    """Send gimbal rotate command safely."""
    pitch = max(min(pitch, GIMBAL_MAX_PITCH), GIMBAL_MIN_PITCH)
    yaw = max(min(yaw, GIMBAL_MAX_YAW), GIMBAL_MIN_YAW)
    payload = json.dumps({
        "mode": 65535,
        "pitch": pitch,
        "roll": 0,
        "yaw": yaw,
        "pitchIgnored": False,
        "rollIgnored": True,
        "yawIgnored": False,
        "duration": 0.3,
        "jointReferenceUsed": False,
        "timeout": 2
    })
    drone.action("Gimbal", "RotateByAngle", payload)

def reset_gimbal(drone):
    """Reset gimbal to forward orientation (pitch=0, yaw=0)."""
    global current_pitch, current_yaw
    current_pitch = 0
    current_yaw = 0
    send_gimbal(drone, current_pitch, current_yaw)


def look_down(drone):
    """Point gimbal straight down."""
    global current_pitch
    current_pitch = GIMBAL_MIN_PITCH
    send_gimbal(drone, current_pitch, current_yaw)

# ----------------------------
# MAIN PROGRAM
# ----------------------------
with OpenDJI(IP_ADDR) as drone:
    print("Press 'X' to exit program.")

    last_key_state = {k: False for k in ['8','2','4','6','5','0']}

    while True:
        try:
            if keyboard.is_pressed('x'):
                break

            # --- Video frame ---
            frame = drone.getFrame()
            if frame is None or not isinstance(frame, np.ndarray):
                frame = BLANK_FRAME.copy()
            else:
                frame = cv2.resize(frame, dsize=None, fx=SCALE_FACTOR, fy=SCALE_FACTOR)
            cv2.imshow("Live Video", frame)
            cv2.waitKey(1)

            # --- Drone movement ---
            keys_to_check = ['w','s','a','d','up','down','left','right','1','2','3','4']
            keys = {k: keyboard.is_pressed(k) for k in keys_to_check}

            yaw_move = ROTATE_VALUE * (keys.get('d',0) - keys.get('a',0))
            ascent = MOVE_VALUE * (keys.get('w',0) - keys.get('s',0))
            roll = MOVE_VALUE * (keys.get('right',0) - keys.get('left',0))
            pitch_move = MOVE_VALUE * (keys.get('up',0) - keys.get('down',0))
            drone.move(yaw_move, ascent, roll, pitch_move)

            # --- Drone commands ---
            if keys.get('1', False): print(drone.takeoff(True))
            if keys.get('2', False): print(drone.land(True))
            if keys.get('3', False): print(drone.enableControl(True))
            if keys.get('4', False): print(drone.disableControl(True))

            # --- Gimbal single-tap controls ---
            for key, action in [('8','pitch_up'), ('2','pitch_down'),
                                ('4','yaw_left'), ('6','yaw_right'),
                                ('5','reset'), ('0','look_down')]:
                pressed = keyboard.is_pressed(key)
                if pressed and not last_key_state[key]:
                    if action == 'pitch_up':
                        current_pitch = min(current_pitch + GIMBAL_STEP_PITCH, GIMBAL_MAX_PITCH)
                        send_gimbal(drone, current_pitch, current_yaw)
                    elif action == 'pitch_down':
                        current_pitch = max(current_pitch - GIMBAL_STEP_PITCH, GIMBAL_MIN_PITCH)
                        send_gimbal(drone, current_pitch, current_yaw)
                    elif action == 'yaw_left':
                        current_yaw = max(current_yaw - GIMBAL_STEP_YAW, GIMBAL_MIN_YAW)
                        send_gimbal(drone, current_pitch, current_yaw)
                    elif action == 'yaw_right':
                        current_yaw = min(current_yaw + GIMBAL_STEP_YAW, GIMBAL_MAX_YAW)
                        send_gimbal(drone, current_pitch, current_yaw)
                    elif action == 'reset':
                        # RESET BOTH PITCH AND YAW
                        reset_gimbal(drone)
                    elif action == 'look_down':
                        look_down(drone)

                last_key_state[key] = pressed


        except Exception as e:
            # Catch everything to prevent crash
            print(f"Error: {e}")
            time.sleep(0.05)

cv2.destroyAllWindows()
