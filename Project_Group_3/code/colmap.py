import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime
from pypylon import pylon
from pypylon import genicam
import subprocess


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
MOTOR_V=500                 # default motor speed
RUN_TIME = 1                # default motor running time

# servo parameter
MIN_POS = 100               # min pos
MAX_POS = 1000              # max pos
SERVO_SPEED = 2000          # speed
SERVO_TIME = 0              # running time, 0 denote no strict

# project path
PROJECT_PATH = "D:\\zju\\dasanshang\\Intelligent_version\\test"
COLMAP_BAT = "D:\\1\\colmap\\colmap-x64-windows-nocuda\\COLMAP.bat"

# Plat: 1 unit represents a half-circle rotation (180 degrees)
# Frame rotation range: -80 degrees to 600 degrees; vertical position at 450 degrees
PLAT_COUNT = 7
FRAME_COUNT = 7

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

default_cameraSettings = {
    'r_balance': 1,
    'g_balance': 1,
    'b_balance': 1,
    'gain_db': 4.86,      
    'exposure_time': 67680,   
    'PixelFormat': 'RGB8',
    'gamma': 1.0
}

def OpenFirstCamera():
    """Open the first available camera"""
    devices = pylon.TlFactory.GetInstance().EnumerateDevices()
    if len(devices) == 0:
        return None
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[0]))
    camera.Open()
    return camera

def SetCamera(camera, cameraSettings):
    """Initialize basic camera parameters"""
    # Set pixel format
    camera.PixelFormat.SetValue(cameraSettings['PixelFormat'])
    camera.UserSetSelector = "Default"
    camera.UserSetLoad.Execute()
    
    # Disable auto white balance and use manual balance parameters
    camera.BalanceWhiteAuto.SetValue("Off")
    camera.BalanceRatioSelector.SetValue("Red")
    camera.BalanceRatio.SetValue(cameraSettings['r_balance'])
    camera.BalanceRatioSelector.SetValue("Green")
    camera.BalanceRatio.SetValue(cameraSettings['g_balance'])
    camera.BalanceRatioSelector.SetValue("Blue")
    camera.BalanceRatio.SetValue(cameraSettings['b_balance'])
    
    # Disable auto exposure/auto gain and use manual parameters
    camera.ExposureAuto.SetValue("Off")
    camera.ExposureTime.SetValue(cameraSettings['exposure_time'])
    camera.GainAuto.SetValue("Off")
    camera.Gain.Value = cameraSettings['gain_db']

def Ycbcr422_to_rgb(ycbcr422):
    """Convert YCbCr422 to RGB (camera raw data format conversion)"""
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
    try:
        # Wait for parameters to stabilize
        cv2.waitKey(200)
        
        # Retrieve image (5-second timeout)
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grabResult.GrabSucceeded():    
            # Format conversion            
            img_rgb = Ycbcr422_to_rgb(grabResult.Array)
            # Generate filename (correct angle correspondence, retain decimal to avoid duplicate names)
            # Keep 1 decimal place for angles to avoid floating-point confusion
            filename = f"photo_plat{plat_angle:.1f}_frame{frame_angle:.1f}.png"
            save_path = os.path.join(save_dir, filename)
            
            # Save image: RGB to BGR (OpenCV's default save format)
            cv2.imwrite(save_path, img_rgb) #cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
            
            print(f"Photo captured successfully! File: {filename} | Platform angle: {plat_angle:.1f}° | Frame angle: {frame_angle:.1f}°")
        
        grabResult.Release()
        return True
        
    except genicam.GenericException as e:
        print(f"Camera error (Platform {plat_angle:.1f}°, Frame {frame_angle:.1f}°): {e}")
        return False
    except Exception as e:
        print(f"Photo capture error (Platform {plat_angle:.1f}°, Frame {frame_angle:.1f}°): {e}")
        return False


def create_dir_if_not_exist(dir_path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"\ncreate path: {dir_path}")

def delete_file_if_exist(file_path):
    """Delete file if it exists"""
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"delete: {file_path}")

def run_colmap_command(command, step_name):
    """Execute COLMAP command and output logs"""
    print(f"[COLMAP STEP {step_name}] :")
    
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        print(result.stdout)
        print(f"[COLMAP STEP {step_name}] Execution successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[COLMAP STEP {step_name}] Execution failed! Error message:")
        print(e.stdout)
        return False
    except Exception as e:
        print(f"[COLMAP STEP {step_name}] Exception occurred: {str(e)}")
        return False

def colmap_3d_reconstruction():
    """COLMAP 3D reconstruction main function (uses original batch script configuration)"""
    # Path configuration (consistent with original batch script)
    IMAGE_PATH = os.path.join(PROJECT_PATH, "images")  # Consistent with photo save path in original code
    DB_PATH = os.path.join(PROJECT_PATH, "database.db")
    SPARSE_PATH = os.path.join(PROJECT_PATH, "sparse")
    DENSE_PATH = os.path.join(PROJECT_PATH, "dense")
    

    # Check if COLMAP.bat is valid
    if not os.path.exists(COLMAP_BAT):
        print(f"Error: COLMAP.bat not found at {COLMAP_BAT}! Please check the path.")
        return False
    if not os.access(COLMAP_BAT, os.X_OK):
        print(f"Error: COLMAP.bat is not executable! Check file permissions.")
        return False

    # Initialize directories and delete old files
    print("Initialize COLMAP workspace directories")
    create_dir_if_not_exist(SPARSE_PATH)
    create_dir_if_not_exist(DENSE_PATH)
    delete_file_if_exist(DB_PATH)

    # Execute COLMAP steps 
    # Step 1: Feature Extraction
    if not run_colmap_command([
        "cmd", "/c", COLMAP_BAT,
        "feature_extractor",
        "--database_path", DB_PATH,
        "--image_path", IMAGE_PATH,
        "--ImageReader.single_camera", "1",
        "--SiftExtraction.num_threads", "8",
        "--SiftExtraction.use_gpu", "1"
    ], "1/7 - Feature Extraction"):
        return False

    # Step 2: Feature Matching
    if not run_colmap_command([
        "cmd", "/c", COLMAP_BAT,
        "exhaustive_matcher",
        "--database_path", DB_PATH,
        "--SiftMatching.num_threads", "8",
        "--SiftMatching.use_gpu", "1"
    ], "2/7 - Feature Matching"):
        return False

    # Step 3: Sparse Reconstruction
    if not run_colmap_command([
        "cmd", "/c", COLMAP_BAT,
        "mapper",
        "--database_path", DB_PATH,
        "--image_path", IMAGE_PATH,
        "--output_path", SPARSE_PATH,
        "--Mapper.num_threads", "8",
        "--Mapper.init_min_tri_angle", "4"
    ], "3/7 - Sparse Reconstruction"):
        return False

    # Step 4: Image Undistortion
    if not run_colmap_command([
        "cmd", "/c", COLMAP_BAT,
        "image_undistorter",
        "--image_path", IMAGE_PATH,
        "--input_path", os.path.join(SPARSE_PATH, "0"),
        "--output_path", DENSE_PATH,
        "--output_type", "COLMAP",
        "--max_image_size", "1600"
    ], "4/7 - Image Undistortion"):
        return False

    # Step 5: Dense Reconstruction (PatchMatch Stereo)
    if not run_colmap_command([
        "cmd", "/c", COLMAP_BAT,
        "patch_match_stereo",
        "--workspace_path", DENSE_PATH,
        "--workspace_format", "COLMAP",
        "--PatchMatchStereo.geom_consistency", "true",
        "--PatchMatchStereo.max_image_size", "1600",
        "--PatchMatchStereo.window_radius", "3",
        "--PatchMatchStereo.num_samples", "8",
        "--PatchMatchStereo.num_iterations", "3",
        "--PatchMatchStereo.filter", "true"
    ], "5/7 - Dense Reconstruction (PatchMatch Stereo)"):
        return False

    # Step 6: Stereo Fusion (Dense Point Cloud)
    if not run_colmap_command([
        "cmd", "/c", COLMAP_BAT,
        "stereo_fusion",
        "--workspace_path", DENSE_PATH,
        "--workspace_format", "COLMAP",
        "--input_type", "geometric",
        "--output_path", os.path.join(DENSE_PATH, "fused.ply")
    ], "6/7 - Stereo Fusion (Dense Point Cloud)"):
        return False

    # Step 7: Surface Meshing
    if not run_colmap_command([
        "cmd", "/c", COLMAP_BAT,
        "poisson_mesher",
        "--input_path", os.path.join(DENSE_PATH, "fused.ply"),
        "--output_path", os.path.join(DENSE_PATH, "meshed-poisson.ply")
    ], "7/7 - Surface Meshing"):
        return False

    # Output result paths
    print("All COLMAP 3D reconstruction steps completed successfully!")
    print(f"Sparse reconstruction results: {os.path.join(SPARSE_PATH, '0')}")
    print(f"Dense point cloud file: {os.path.join(DENSE_PATH, 'fused.ply')}")
    print(f"Mesh model file: {os.path.join(DENSE_PATH, 'meshed-poisson.ply')}")
    return True

def main():
    # Create image save directory (create if not exists)
    save_dir = os.path.join(PROJECT_PATH, "images")                              
    os.makedirs(save_dir, exist_ok=True)
    
    # Initialize camera (Basler pylon)
    camera = OpenFirstCamera()
    if camera is None:
        print("No camera found")
        return
    try:
        # Apply default camera settings
        SetCamera(camera, default_cameraSettings)
        # Start continuous image grabbing 
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)        
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
            # Reset frame to initial position (0 angle) before starting
            rotateFrame(0)
            time.sleep(1.0)  # Wait for frame to stabilize
            
            for i in range(PLAT_COUNT):
                plat_angle = i * 360 / PLAT_COUNT
                for j in range (FRAME_COUNT):
                    # Calculate current and next frame angles 
                    frame_angle = j * 90 / FRAME_COUNT
                    next_frame_angle = ( j + 1 ) * 90 / FRAME_COUNT
                    
                    # Capture image at current platform-frame angle
                    time.sleep(0.5)
                    take_photo(camera, save_dir, plat_angle, frame_angle)
                    time.sleep(0.5)
                    
                    # Rotate frame to next position for next capture
                    rotateFrame(int(next_frame_angle * 5))
                    time.sleep(0.5)
                
                time.sleep(0.5)
                rotatePlat(1 / PLAT_COUNT)
                # Reset frame to initial position for next platform cycle
                rotateFrame(0)
                time.sleep(1.5) # Longer delay for platform stability
            '''
            for i in range(FRAME_COUNT):
                # Calculate current frame angle 
                frame_angle = i * 90 / FRAME_COUNT
                next_frame_angle = ( i + 1 ) * 90 / FRAME_COUNT
                for j in range(PLAT_COUNT):
                    # Calculate current platform angle
                    plat_angle = j * 360 / PLAT_COUNT
                    
                    # Capture image at current frame-platform angle
                    time.sleep(0.5)
                    take_photo(camera, save_dir, plat_angle, frame_angle)
                    
                    # Rotate platform to next position for next capture
                    time.sleep(0.5)
                    rotatePlat(2 / PLAT_COUNT)
                    time.sleep(0.5)
                
                time.sleep(0.5)
                rotateFrame(int(next_frame_angle * 5))
                time.sleep(0.5)
            '''
            # Capture one final image at frame 90deg
            take_photo(camera, save_dir, 0, 90)

            # Start COLMAP 3D reconstruction with captured images
            print("Photo capture completed, starting COLMAP 3D reconstruction...")
            colmap_3d_reconstruction()
        except:
            print("error")
            
    finally:
        # Reset platform to initial position
        rotatePlat(0)
        portHandler.closePort()
        if camera is not None and camera.IsOpen():
            camera.StopGrabbing()
            camera.Close()
        cv2.destroyAllWindows()
        print("done")


if __name__ == "__main__":
    main()
