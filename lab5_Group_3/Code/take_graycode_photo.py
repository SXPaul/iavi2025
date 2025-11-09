import os
import time
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np
from datetime import datetime
from pypylon import pylon
from pypylon import genicam
import subprocess

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
    
    # Disable auto white balance, use manual balance parameters
    camera.BalanceWhiteAuto.SetValue("Off")
    camera.BalanceRatioSelector.SetValue("Red")
    camera.BalanceRatio.SetValue(cameraSettings['r_balance'])
    camera.BalanceRatioSelector.SetValue("Green")
    camera.BalanceRatio.SetValue(cameraSettings['g_balance'])
    camera.BalanceRatioSelector.SetValue("Blue")
    camera.BalanceRatio.SetValue(cameraSettings['b_balance'])
    
    # Disable auto exposure/auto gain, use manual parameters
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

def take_photo(camera, save_dir, img_name):
    try:
        # Wait for parameters to stabilize
        cv2.waitKey(200)
        
        # Acquire image (timeout: 5 seconds)
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grabResult.GrabSucceeded():    
            # Format conversion            
            img_rgb = Ycbcr422_to_rgb(grabResult.Array)
            
            # Generate filename: prepend "captured_" to the original image name, keep the original extension
            base_name = os.path.splitext(img_name)[0]
            filename = f"captured_{base_name}.png"
            save_path = os.path.join(save_dir, filename)
            
            # Save image
            cv2.imwrite(save_path, img_rgb)
            
            print(f"Photo taken successfully! File: {filename}")
        
        grabResult.Release()
        return True
        
    except genicam.GenericException as e:
        print(f"Camera error: {str(e)}")
        return False
    except Exception as e:
        print(f"Photo capture error: {str(e)}")
        return False
    
    
class ProjectorController:
    def __init__(self, image_dir, save_dir):
        """Projector control and photo capture synchronization program"""
        self.image_dir = image_dir
        self.save_dir = save_dir
        #self.images = self._get_images()
        self.images = self._get_sorted_images()  # Get sorted pattern list
        
        # Create save directory
        os.makedirs(save_dir, exist_ok=True)
        
        # Initialize camera 
        self.camera = None
        self._init_camera()
        
        # Create display window
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)  # Fullscreen display
        self.root.configure(bg='black')
        self.label = tk.Label(self.root, bg='black')
        self.label.pack(fill=tk.BOTH, expand=True)
        
        # Bind ESC key to exit fullscreen
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        
        self.current_index = 0

    def _get_images(self):
        """Read all .png format images in the directory (no sorting, return in default system directory order)"""
        # Filter all files with .png extension in the directory (case-insensitive, e.g., .PNG is also matched)
        png_images = [
            f for f in os.listdir(self.image_dir)
            if f.lower().endswith('.png')
        ]
        # Return all matched images directly (order is default system directory order)
        return png_images
    
    def _get_sorted_images(self):
        """Get sorted image list in standard structured light order"""
        image_extensions = ('.png', '.jpg', '.jpeg')
        all_images = [f for f in os.listdir(self.image_dir) 
                     if f.lower().endswith(image_extensions)]
        
        # 1. Extract reference patterns (all white, all black), ensure all white comes first
        white_ref = [f for f in all_images if f == 'reference_white.png']
        black_ref = [f for f in all_images if f == 'reference_black.png']
        ref_images = white_ref + black_ref  # Fixed order: all white first, then all black
        
        # 2. Extract vertical Gray code patterns
        vertical_patterns = [f for f in all_images if 'vertical' in f and 'graycode' in f]
        # Sort by bit number (bit00 → bit01 → ... → bit09), normal pattern first then inverted for each bit
        vertical_patterns.sort(key=lambda x: (
            int(x.split('bit')[1].split('_')[0]),  # Sort by bit number
            0 if 'normal' in x else 1  # Normal pattern comes first, inverted comes later
        ))
        
        # 3. Extract horizontal Gray code patterns
        horizontal_patterns = [f for f in all_images if 'horizontal' in f and 'graycode' in f]
        #同样按位序号排序，每个位先正常后反相
        horizontal_patterns.sort(key=lambda x: (
            int(x.split('bit')[1].split('_')[0]),  # Sort by bit number
            0 if 'normal' in x else 1  # Normal pattern comes first, inverted comes later
        ))
        
        # Final order: reference images → vertical Gray code → horizontal Gray code
        return ref_images + vertical_patterns + horizontal_patterns

    def _init_camera(self):
        """Initialize camera"""
        print("Initializing camera...")
        self.camera = OpenFirstCamera()
        if not self.camera:
            raise Exception("Failed to open camera, please check camera connection")
        
        # Camera settings (adjust according to actual conditions)
        camera_settings = {
            'PixelFormat': "YCbCr422_8",
            'exposure_time': 30000,  # Exposure time (microseconds)
            'gain_db': 10,           # Gain
            'r_balance': 1.0,        # Red balance
            'g_balance': 1.0,        # Green balance
            'b_balance': 1.0         # Blue balance
        }
        
        SetCamera(self.camera, camera_settings)
        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        print("Camera initialized successfully and started grabbing")

    def show_and_capture(self):
        """Display image and synchronize photo capture"""
        if self.current_index >= len(self.images):
            print("All images processed")
            self.root.destroy()
            return
        
        # Get current image path
        img_name = self.images[self.current_index]
        img_path = os.path.join(self.image_dir, img_name)
        
        try:
            # Display image
            print(f"Displaying: {img_name}")
            img = Image.open(img_path)
            
            # Resize image to fit screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            img = img.resize((screen_width, screen_height), Image.LANCZOS)
            
            # Display image
            tk_img = ImageTk.PhotoImage(image=img)
            self.label.config(image=tk_img)
            self.label.image = tk_img  # Keep reference
            
            # Wait for display to stabilize
            self.root.update()
            time.sleep(1)  # Adjust according to projector response speed
            
            # Capture photo
            print(f"Capturing photo {self.current_index + 1}/{len(self.images)}")
            success = take_photo(
                self.camera, 
                self.save_dir, 
                img_name  # Pass the name of the currently displayed image to generate corresponding captured filename
            )
            if not success:
                print(f"Failed to capture photo {self.current_index + 1}")
            
            # Proceed to next image
            self.current_index += 1
            self.root.after(200, self.show_and_capture)  # Process next image after 0.2 seconds
            
        except Exception as e:
            print(f"Error processing image {img_name}: {str(e)}")
            self.root.destroy()

    def start(self):
        """Start display and photo capture process"""
        print(f"Found {len(self.images)} images, starting processing...")
        self.root.after(1000, self.show_and_capture)  # Start after 1 second delay
        self.root.mainloop()
        
        # Close camera
        if self.camera:
            self.camera.StopGrabbing()
            self.camera.Close()
        print("All operations completed, camera closed")

if __name__ == "__main__":
    # Configure paths (modify according to actual conditions)
    #GRAYCODE_DIR = "Pattern-0"
    GRAYCODE_DIR = "gray_png_new"
    SAVE_DIR = os.path.join(os.path.dirname(GRAYCODE_DIR), "night/2_1")  # Captured photos save directory
    
    try:
        controller = ProjectorController(GRAYCODE_DIR, SAVE_DIR)
        controller.start()
    except Exception as e:
        print(f"Program error: {str(e)}")