"""
Control the No. 1 servo to rotate as a motor, while the No. 2 and No. 3 servos
rotate synchronously in opposite directions (at the same Angle but in 
opposite directions).
"""
import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime
from pypylon import pylon
from pypylon import genicam


if os.name == 'nt':
    import msvcrt
    def getch():
        return msvcrt.getch().decode()
else:
    import tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

sys.path.append("..")
from scservo_sdk import *

# basic parameter
BAUDRATE = 1000000          # sc servo's baudrate is 1000000
DEVICENAME = 'COM3'        # check in  Device Manager
MOTOR_ID = 1                # motor id
SYNC_SERVO_IDS = [2, 3]     # servo id
LEFT_SYNC_SERVO_ID=2        # left servo id
RIGHT_SYNC_SERVO_ID=3       # right servo id
LEFT_INIT_ANGLE=350         # left servo initial angle
RIGHT_INIT_ANGLE=720        # right servo initial angle
MOTOR_V=-300                 # default motor speed
RUN_TIME = 1                # default motor running time

# servo parameter
MIN_POS = 100               # min pos
MAX_POS = 1000              # max pos
SERVO_SPEED = 2000          # speed
SERVO_TIME = 0              # running time, 0 denote no strict

# initial lize port and protocol
portHandler = PortHandler(DEVICENAME)
# Initialize PacketHandler instance
# Get methods and members of Protocol
packetHandler = scscl(portHandler)
    

def startMotor(v=MOTOR_V):
    scs_comm_result, scs_error = packetHandler.PWMMode(MOTOR_ID)
    if scs_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(scs_comm_result))
    elif scs_error != 0:
        print("%s" % packetHandler.getRxPacketError(scs_error))  
    scs_comm_result, scs_error = packetHandler.WritePWM(MOTOR_ID, v)
    if scs_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(scs_comm_result))
    if scs_error != 0:
        print("%s" % packetHandler.getRxPacketError(scs_error))

def rotateFrame(angle=0):
    """Function to operate the robot arm that fix the camera
    Args:
        angle (int, optional):Position of the robot arm.A integer of [0,600] ,
                    where 0 denote the robot arm is parallel to the horizontal plane.
                    The larger the number, the higher the robot arm's position. 
                    400 indicates a vertical position to the ground
                    Defaults to 0.
    """
    scs_comm_result, scs_error = packetHandler.RegWritePos(LEFT_SYNC_SERVO_ID,LEFT_INIT_ANGLE+angle, 0, SERVO_SPEED)
    if scs_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(scs_comm_result))
        print(1)
    if scs_error != 0:
        print("%s" % packetHandler.getRxPacketError(scs_error))
        print(2)
    scs_comm_result, scs_error = packetHandler.RegWritePos(RIGHT_SYNC_SERVO_ID, RIGHT_INIT_ANGLE-angle, 0, SERVO_SPEED)
    if scs_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(scs_comm_result))
        print(1)
    if scs_error != 0:
        print("%s" % packetHandler.getRxPacketError(scs_error))
        print(2)        
    packetHandler.action(LEFT_SYNC_SERVO_ID)
    packetHandler.action(RIGHT_SYNC_SERVO_ID)

def rotatePlat(duration=RUN_TIME,v=MOTOR_V):
    """Function to operate the plat.
    Attention!!!The unit of duratioin is second!!!
    Args:
        duration (int, optional): give the duratino time that you want the motor rotate for.
        Defaults to RUN_TIME.
        v (int, optional): give the speed of motor you want the motor to rotate at. Defaults to MOTOR_V.
    """
    startMotor(v)
    # wait for a while and stop the motor
    time.sleep(duration) 
    startMotor(0)




# Default camera parameters
default_cameraSettings = {
    'r_balance': 1,
    'g_balance': 1,
    'b_balance': 1,
    'gain_db': 10,
    'exposure_time': 500,
    'PixelFormat': 'RGB8',
    'gamma': 1.0
}

def OpenFirstCamera():
    devices = pylon.TlFactory.GetInstance().EnumerateDevices()
    if len(devices) == 0:
        return None
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[0]))
    camera.Open()
    return camera

def SetCamera(camera, cameraSettings):
    camera.PixelFormat.SetValue(cameraSettings['PixelFormat'])
    camera.UserSetSelector = "Default"
    camera.UserSetLoad.Execute()
    
    camera.BalanceWhiteAuto.SetValue("Off")
    camera.BalanceRatioSelector.SetValue("Red")
    camera.BalanceRatio.SetValue(cameraSettings['r_balance'])
    camera.BalanceRatioSelector.SetValue("Green")
    camera.BalanceRatio.SetValue(cameraSettings['g_balance'])
    camera.BalanceRatioSelector.SetValue("Blue")
    camera.BalanceRatio.SetValue(cameraSettings['b_balance'])
    
    camera.ExposureAuto.SetValue("Off")
    camera.ExposureTime.SetValue(cameraSettings['exposure_time'])
    camera.GainAuto.SetValue("Off")
    camera.Gain.Value = cameraSettings['gain_db']

def Ycbcr422_to_rgb(ycbcr422):
    height, width, _ = ycbcr422.shape
    y_plane = ycbcr422[:, :, 0]
    cbcr_plane = ycbcr422[:, :, 1]

    cb_plane = np.zeros((height, width), dtype=np.uint8)
    cr_plane = np.zeros((height, width), dtype=np.uint8)

    cb_plane[:, ::2] = cbcr_plane[:, ::2]
    cr_plane[:, ::2] = cbcr_plane[:, 1::2]
    cb_plane[:, 1::2] = cbcr_plane[:, ::2]
    cr_plane[:, 1::2] = cbcr_plane[:, 1::2]

    ycbcr_full = np.dstack((y_plane, cb_plane, cr_plane))
    return cv2.cvtColor(ycbcr_full, cv2.COLOR_YCrCb2RGB)

def take_photo(camera, save_dir, plat_angle, frame_angle):
    """
    This function is to take photo with the passed-in camera
    and save photo in save_dir named with plat angle and frame angle
    """
    try:
        cv2.waitKey(200)
        
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grabResult.GrabSucceeded():
            if camera.PixelFormat.GetValue() == 'YCbCr422_8':
                img_rgb = Ycbcr422_to_rgb(grabResult.Array)
            else: 
                img_rgb = grabResult.Array
            
            filename = f"photo_plat{plat_angle:.1f}_frame{frame_angle:.1f}.png"
            save_path = os.path.join(save_dir, filename)
            
            cv2.imwrite(save_path, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
            
            print(f"sucessfully take photo!:{filename} | plat angle{plat_angle:.1f}° | frame angle{frame_angle:.1f}°")
        
        grabResult.Release()
        return True
        
    except genicam.GenericException as e:
        print(f"camera error (plat{plat_angle:.1f}°,frame{frame_angle:.1f}°）：{e}")
        return False
    except Exception as e:
        print(f"camera error (plat{plat_angle:.1f}°,frame{frame_angle:.1f}°）：{e}")
        return False


"""
Here give a example to use the two function.
In fact ,you just need to call the two function as the way in  'try ··· finally' 
"""
PLAT_COUNT = 5
FRAME_COUNT = 2

def main():
    
    try:
        # Open port
        if portHandler.openPort():
            print("Succeeded to open the port")
        else:
            print("Failed to open the port")
            print("Press any key to terminate...")
            getch()
            quit()
            
        # Set port baudrate
        if portHandler.setBaudRate(BAUDRATE):
            print("Succeeded to change the baudrate")
        else:
            print("Failed to change the baudrate")
            print("Press any key to terminate...")
            getch()
            quit()

        try:
            rotatePlat(2)
                
        except:
            print("error")
            
    finally:
        portHandler.closePort()
        if camera is not None and camera.IsOpen():
            camera.StopGrabbing()
            camera.Close()
        cv2.destroyAllWindows()
        print("done")

if __name__ == "__main__":
    main()
