# A Shooting System for 3D Point Cloud Construction and Compatible with VGGT

## 1. Introduction

## 2. Setup & Environment

### 2.0. Environment Requirements
```plaintext
Windows11 24H2
NVIDIA GeForce RTX 4060 Laptop GPU 16G

python 3.10.7
pyserial==3.5
Torch 2.3.1 + Cuda 12.1

colmap-x64-windows-cuda 3.12.6

VGGT-1B
```

### 2.1. Hardware Framework

#### 2.1.1 Overall Architecture Overview
The hardware part uses three SC15 servo driver boards, a 12V power supply and some wooden consumables to build an automated photography platform.

![alt text](img/d3534f31b4650e2755809ad0a90540a4.jpg)

The workflow is as follow:
![alt text](img/result.png)

We input a timed and rated PWM wave to the servo of ID1 to use it as a motor, and control its rotation Angle through speed and time.

In addition, we use the functions of the ID2,3 servos themselves to control the rotation Angle of the rocker arm.

Combining various purchased wooden consumables such as screws, a hardware platform was built


#### 2.1.2 Key Hardware Components

##### Hardware assembly
We used 30 * 30 * 1(cm) square wooden boards as the base, a circular wooden board with a diameter of 15(cm) and a thickness of 0.6(cm) as the rotating platform, 10* 1 *0.5(cm) wooden strips to build the mechanical arm, and various types of self-tapping screws and L-shaped fasteners to construct the hardware platform.

![alt text](img/73c49f57e19dd0242c6559da122e64a2.jpg)

Since using self-tapping screws directly would cause the wood to crack and get damaged, we first drill holes at the designed positions with an electric drill and then fix them.

![alt text](img/89a0d2211c6eed5349f082a57863b188.jpg)

##### Motion control module
- Drive unit: [SC15 servo](https://www.waveshare.net/wiki/SC15_Servo#.E5.BC.80.E6.BA.90.E9.A1.B9.E7.9B.AE)
    ![alt text](img/6b6116b1cce821e19f7eb3f0c4e99630.jpg)
- Control board: [Bus Servo Adapter (A)](https://www.waveshare.net/wiki/Bus_Servo_Adapter_(A))
    ![alt text](img/image1.png)
##### Software environment

### 2.2. Classic Workflow with COLMAP

### 2.3. Works on VGGT

## 3. Analysis and Discussion

## 4. Conclusion

## 5. References & Acknowledgements