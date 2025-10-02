#j drone test 1

from jdrone import OpenDJI

import keyboard
import cv2
import numpy as np

"""
    press F - to takeoff the drone.
    press R - to land the drone.
    press E - to enable control from keyboard (joystick disabled)
    press Q - to disable control from keyboard (joystick enabled)
    press X - to close the problam

    press W/S - to move up/down (ascent)
    press A/D - to rotate left/right (yaw control)
    press ↑/↓ - to move forward/backward (pitch)
    press ←/→ - to move left/right (roll)
"""


IP_ADDR = "192.168.0.247"



SCALE_FACTOR = 0.5


MOVE_VALUE = 0.015
ROTATE_VALUE = 0.15


BLANK_FRAME = np.zeros((1080, 1920, 3))
BLNAK_FRAME = cv2.putText(BLANK_FRAME, "No Image", (200, 300),
                          cv2.FONT_HERSHEY_DUPLEX, 10,
                          (255, 255, 255), 15)


with OpenDJI(IP_ADDR) as drone:

    
    print("Press 'x' to close the program")
    while not keyboard.is_pressed('x'):

        
        
        frame = drone.getFrame()

        
        if frame is None:
            frame = BLANK_FRAME
    
        
        frame = cv2.resize(frame, dsize = None,
                           fx = SCALE_FACTOR,
                           fy = SCALE_FACTOR)
        
        
        cv2.imshow("Live video", frame)
        cv2.waitKey(20)
        
        
        
        yaw = 0.0       
        ascent = 0.0    
        roll = 0.0      
        pitch = 0.0     

        
        if keyboard.is_pressed('a'): yaw = -ROTATE_VALUE
        if keyboard.is_pressed('d'): yaw =  ROTATE_VALUE
        if keyboard.is_pressed('s'): ascent  = -MOVE_VALUE
        if keyboard.is_pressed('w'): ascent  =  MOVE_VALUE

        if keyboard.is_pressed('left'):  roll = -MOVE_VALUE
        if keyboard.is_pressed('right'): roll =  MOVE_VALUE
        if keyboard.is_pressed('down'):  pitch = -MOVE_VALUE
        if keyboard.is_pressed('up'):    pitch =  MOVE_VALUE

        
        drone.move(yaw, ascent, roll, pitch)

        
        if keyboard.is_pressed('f'): print(drone.takeoff(True))
        if keyboard.is_pressed('r'): print(drone.land(True))
        if keyboard.is_pressed('e'): print(drone.enableControl(True))
        if keyboard.is_pressed('q'): print(drone.disableControl(True))
