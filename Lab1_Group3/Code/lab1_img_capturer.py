import os
import sys
import cv2
import numpy as np
import csv
from datetime import datetime
from pypylon import pylon
from pypylon import genicam

# 默认相机参数设置
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
    """设置相机参数"""
    # 设置像素格式
    camera.PixelFormat.SetValue(cameraSettings['PixelFormat'])
    camera.UserSetSelector = "Default"
    camera.UserSetLoad.Execute()
    
    # 关闭白平衡
    camera.BalanceWhiteAuto.SetValue("Off")
    camera.BalanceRatioSelector.SetValue("Red")
    camera.BalanceRatio.SetValue(cameraSettings['r_balance'])
    camera.BalanceRatioSelector.SetValue("Green")
    camera.BalanceRatio.SetValue(cameraSettings['g_balance'])
    camera.BalanceRatioSelector.SetValue("Blue")
    camera.BalanceRatio.SetValue(cameraSettings['b_balance'])
    
    # 关闭自动曝光
    camera.ExposureAuto.SetValue("Off")
    camera.ExposureTime.SetValue(cameraSettings['exposure_time'])
    
    # 关闭自动设置增益
    camera.GainAuto.SetValue("Off")
    camera.Gain.Value = cameraSettings['gain_db']

def Ycbcr422_to_rgb(ycbcr422):
    """将Ycbcr422格式转换为RGB格式"""
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
    rgb = cv2.cvtColor(ycbcr_full, cv2.COLOR_YCrCb2RGB)
    return rgb

def calculate_average_brightness(image):
    """计算图像平均亮度"""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return np.mean(gray)

def capture_with_params(camera, save_dir, exp_value, gain_value, image_count, group):
    """使用指定参数拍摄单张照片并记录数据"""
    try:
        camera.ExposureTime.SetValue(exp_value)
        camera.Gain.Value = gain_value
        
        cv2.waitKey(300) 
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grabResult.GrabSucceeded():
            img = Ycbcr422_to_rgb(grabResult.Array)
    
            # 计算亮度
            brightness = calculate_average_brightness(img)
            brightness_rounded = int(round(brightness, 1) * 10)
            
            # 显示图像和参数
            display_img = cv2.resize(img, None, None, fx=0.2, fy=0.2)
            cv2.putText(display_img, f"Exp: {exp_value}us", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(display_img, f"Gain: {gain_value}dB", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(display_img, f"Bright: {brightness:.1f}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow('Capturing...', display_img)
            cv2.waitKey(50) 
            
            # 保存图像
            filename = f"img_{image_count:04}_exp{exp_value}_gain{gain_value}_bright{brightness_rounded}.png"
            save_path = os.path.join(save_dir, filename)
            
            Img = pylon.PylonImage()
            Img.AttachGrabResultBuffer(grabResult)
            Img.Save(pylon.ImageFileFormat_Png, save_path)
            
            print(f"Saved: {filename} | Exp: {exp_value}us | Gain: {gain_value}dB | Bright: {brightness:.1f}")
            image_count += 1
            
        grabResult.Release()
        return image_count
        
    except genicam.GenericException as e:
        print(f"Error capturing image (exp={exp_value}, gain={gain_value}): {e}")
        return image_count

if __name__ == '__main__':
    main_save_dir = os.path.join(os.getcwd(), f"capture_{datetime.now().strftime('%Y-%m-%d_%H-%M')}")
    os.makedirs(main_save_dir, exist_ok=True)
    
    exitCode = 0
    camera = None
    try:
        camera = OpenFirstCamera()
        if camera is None:
            print("Error:no camera")
            sys.exit(1)
        
        SetCamera(camera, default_cameraSettings)

        # 这里写了两个双重循环，固定不同gain遍历曝光和固定不同曝光遍历gain
        print("\nGroup 1 begin")
        group1_dir = os.path.join(main_save_dir, "group1_gain_vary_exposure")
        os.makedirs(group1_dir, exist_ok=True)
        gain_values = range(2, 25, 2)  # 2,4,6,...,24
        exposure_values = range(500, 25001, 1000)  # 500到25000，步长1000
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        image_count = 0
        for gain in gain_values:
            print(f"\ngain={gain}dB...")
            for exp in exposure_values:
                image_count = capture_with_params(
                    camera, group1_dir, exp, gain, image_count, "group1"
                )
        
        camera.StopGrabbing()
        print(f"\nGroup 1 done,{image_count} images")
        

        print("\nGroup 2 begin")
        group2_dir = os.path.join(main_save_dir, "group2_exposure_vary_gain")
        os.makedirs(group2_dir, exist_ok=True)
        exposure_values2 = range(1000, 25001, 5000)  # 1000,6000,...,25000
        gain_values2 = range(5, 26, 1)  # 5到25，步长1
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        for exp in exposure_values2:
            print(f"\nExposure={exp}us")
            for gain in gain_values2:
                image_count = capture_with_params(
                    camera, group2_dir, exp, gain, image_count, "group2"
                )
        
        camera.StopGrabbing()
        print(f"\nGroup 2 done ,here are {image_count - len(gain_values)*len(exposure_values)} new images")
        print(f"\nCapture done,here are {image_count} images")

        
    except genicam.GenericException as e:
        print(f"Error:{e}")
        exitCode = 1
    finally:
        cv2.destroyAllWindows()
        if camera is not None and camera.IsOpen():
            camera.Close()
    sys.exit(exitCode)
    