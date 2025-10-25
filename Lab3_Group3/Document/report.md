# Lab3 Report: Single Camera Calibration - PLY 3D Visualization & AR Projection
## 1. Basic Part
### 1.1 Experiment Objectives  
Goal 3 & 4:  
This section aims to complete two core tasks based on the previously finished single-camera intrinsic and extrinsic calibration results, strictly relying on the provided code files:  
1. Generate a `.ply` file containing **camera centers** and **chessboard point cloud** for 3D visualization — this verifies the spatial consistency of calibration results.  
2. Implement **Augmented Reality (AR) projection**: Overlay 3D objects onto input images, including colored cubes via `AR_cube.py` and `code.py` . The former realizes real-time projection, while the latter outputs photos of the projected cube


### 1.2 Experiment Setup
#### 1.2.1 Core Parameter Configuration
| Parameter Category       | Specific Settings                                                                 | Source Code Files          | Rationale                                                                 |
|--------------------------|-----------------------------------------------------------------------------------|---------------------------|---------------------------------------------------------------------------|
| Chessboard Parameters    | Inner corners: (11, 8) (columns × rows); Square size: 14.5 mm                        | All code files            | Consistent with the calibration phase (in `code.py`) to ensure world coordinate accuracy. |
| Calibration Data         | Calibration file path: `Calibration_Results/calibration_params.npz` (contains `mtx` (intrinsic matrix), `dist` (distortion coefficients), `rvecs` (rotation vectors), `tvecs` (translation vectors)) | `AR_cube.py`, `generate_ply.py`, | Reuses pre-calibrated intrinsic/extrinsic parameters to avoid re-calibration. |
| PLY Generation Parameters | Chessboard color: red; Camera color: blue | `generate_ply.py`     | Defined in the `generate_ply.py` , make the point cloud look clearer and more straightforward |
| AR Projection (Cube)     | Cube size: 50 mm; Position: `(4×20, 3×20, 0)` = (80, 60, 0) mm; Face colors: blue (255,0,0), green (0,255,0), etc. | `AR_cube.py`, `code.py`   | Cube size/position matches the chessboard grid.The six faces are defined as different colors to facilitate the determination of the correctness of the projection |
| Camera Settings          | Resolution: 1280×720; Camera index: 0 (default); Corner detection flags: `CALIB_CB_ADAPTIVE_THRESH + CALIB_CB_FAST_CHECK + CALIB_CB_NORMALIZE_IMAGE` | `AR_cube.py`              | Reduces resolution to improve real-time performance; detection flags enhance adaptability to light changes. |


#### 1.2.2 Tool & Library Dependencies
- Open3D: Used for point cloud/line set construction in `check_pointcloud.py` .
- OpenCV: Core library for all files—enables `findChessboardCorners` (corner detection), `solvePnP` (extrinsic estimation), `projectPoints` (3D-to-2D projection), and image rendering.  
- NumPy: Data processing tool for all files, used for matrix operations and vertex coordinate handling.  


### 1.3 Experiment Results 
#### 1.3.1 Task 3: PLY File Generation (`generate_ply.py`)

##### Step 1:Load Calibration Parameters
The script reads the `Calibration_Results/calibration_params.npz` file to extract essential extrinsic parameters:
- rvecs: Rotation vectors (each corresponds to one calibration image)
- tvecs: Translation vectors (each corresponds to one calibration image) 


##### Step 2: Generate 3D Coordinates of Chessboard Corners
The correction of "dimension mismatch issues" in the code is critical to ensuring the accuracy of PLY visualization:


##### Step 3: Calculate Camera Centers
For each calibration image, the camera center (3D position of the camera in the world coordinate system) is computed by:
- Converting rotation vectors (rvecs) to rotation matrices via cv2.Rodrigues().
- Applying the formula: $camera_{center} = -R.T @  tvec$  (where R is the rotation matrix, tvec is the translation vector).
- Reshaping the result to ensure dimensional consistency for subsequent processing.
##### Step 4: Export to PLY File
- Merge chessboard corner points and camera center points into a single point cloud.
- Assign colors for distinction: red for chessboard corners, blue for camera centers.
- Write the point cloud data into a .ply file.

***Visualization Result of the Camera-Chessboard System*** 
![alt text](Img/Goal3/Figure_1.png)
![alt text](Img/Goal3/Figure_2.png)
![alt text](Img/Goal3/Figure_3.png)
In the point cloud map, it can be seen that the chessboard plane is in the xy plane,and  camera angles follows the positive direction of the Z-axis

#### 1.3.2 Task 4 & Bonus: AR Projection (Code: `AR_cube.py`, `code.py`)
AR projection is implemented in two scenarios (simple cube and complex cat model) using the corresponding code files. The workflow is consistent, but model preprocessing differs:

##### Scenario 1: Colored Cube Projection (`AR_cube.py`)
###### Step 1: Define Cube Model (`define_colored_cube()` Function)
1. **Vertex Calculation**: For a 50 mm-sized cube centered at (80, 60, 0) mm, calculate the coordinates of 8 vertices:  
   - Half-size = 25 mm; vertices include front (Z=25) and back (Z=-25) faces (e.g., front-left-bottom vertex: `(-25, -25, 25)`).  
   - Translate vertices to the target position: `vertices += cube_position` (ensures the cube is centered and overlaid on the chessboard).  
2. **Face Definition**: Define 6 faces using vertex indices (e.g., front face: `[0,1,2,3]`, back face: `[4,5,6,7]`).  


###### Step 2: Real-Time Projection (`ar_cube_projection()` Function)
1. **Load Calibration Data and Initialize Camera**: Load `mtx` and `dist` via the `load_calibration_params()` function, open the camera, and set the resolution to 1280×720 to balance speed and clarity.  
2. **Corner Detection and Extrinsic Estimation**:  
   - Convert each frame to grayscale, call the `findChessboardCorners` function to detect corners (using adaptive threshold/normalization flags to improve stability).  
   - Refine corners using the `cornerSubPix` function.  
   - Generate chessboard world coordinates `objp`, then call the `solvePnP(objp, corners_refined, mtx, dist)` function to estimate extrinsic parameters—the code uses an "extrinsic cache" optimization: if detection fails, it reuses the `rvec`/`tvec` from the previous frame to avoid model disappearance.  
3. **3D-to-2D Projection and Rendering**:  
   - Vertex projection: `cube_2d, _ = cv2.projectPoints(cube_vertices, rvec, tvec, mtx, dist)`—reshape the result into (8,2) integer pixel coordinates.  
   - Draw semi-transparent faces: Create an overlay, fill each face with `face_colors` using the `fillPoly` function, then blend it with the original frame via the `addWeighted` function.  
   - Draw white edges: Outline face boundaries using the `polylines` function to solve the "boundary blur" issue.  


##### Scenario 2: Cat Model Projection (`AR_cat.py`)
###### Step 1: Model Preprocessing (`load_3d_model()` Function)
1. **Load PLY Model**: Read `cat.ply` using the `o3d.io.read_triangle_mesh()` function, check for the existence of vertices, and raise a `ValueError` if vertices are missing.  
2. **Model Alignment**:  
   - Centering: `vertices = vertices - np.mean(vertices, axis=0)`—moves the model center to the origin.  
   - Scaling: `vertices = vertices * model_scale`—scales the model by 300x to fit the chessboard size.  
   - Z-alignment: `vertices[:, 2] -= np.min(vertices[:, 2])`—lowers the model so its lowest point (feet) has Z=0, avoiding floating.  
   - Translation: `vertices += model_offset`—moves the model to (80, 60, 0) mm, consistent with the cube’s position.  


###### Step 2: Projection and Rendering (`ar_realtime_projection()` Function)
The workflow is consistent with cube projection, except for the rendering method:  
- After projecting vertices to 2D coordinates via the `projectPoints` function, iterate over the model’s triangular faces.  
- For each triangle, obtain the 2D coordinates of its 3 vertices, fill the triangle with magenta `(147,20,255)` using the `fillConvexPoly` function, then draw white edges via the `line` function.  


##### Step 3: AR Projection Results
- **Cube Projection**: As shown in the figure, the cube is stably overlaid on the chessboard—semi-transparent faces do not block the chessboard background, and white edges align with the chessboard grid.  
- **Cat Model Projection**: As shown in the figure, the cat model’s "feet" touch the chessboard surface with a clear outline—proving the effectiveness of the Z-alignment and scaling logic in the `load_3d_model()` function.  
  

*AR Projection Result of Colored Cube*  
![result](./Img/Goal4/ar_cube.png)  
*AR Projection Result of Cat Model*  
![result](./Img/Goal4/ar_cat.png)

*Both of these two screenshots were captured in real time, so there is a minor delay in the AR projection, which leads to a slight misalignment in the displayed AR projection. This phenomenon occurs because I was holding the tablet with one hand while taking screenshots with the other, making it difficult to keep the device stable and resulting in slight tremors.*





### 1.4 Result Analysis & Discussion
#### 1.4.1 PLY Visualization: Code Optimization and Result Reliability
The key to successful PLY file generation lies in **dimension correction** in `check_pointcloud.py`:  
- Before correction, unflattened `rvec`/`tvec` would cause errors in the `cv2.Rodrigues()` function or matrix multiplication. The code ensures all vectors are 3-dimensional via `flatten()[:3]`, resolving shape mismatch issues.  
- The camera model’s line set (axes + frustum) directly reflects the accuracy of extrinsic parameters: If camera views are limited (e.g., only front views), it indicates insufficient view angles during calibration, which would lead to unstable AR projection. The distributed camera centers confirm that the calibration dataset has robustness.  


#### 1.4.2 AR Projection: Code-Driven Stability and Accuracy
1. **Impact of Code Optimization on AR Performance**:  
   - **Extrinsic Cache (`AR_cube.py`)**: When the chessboard is partially occluded, `findChessboardCorners` fails. The code reuses the `rvec`/`tvec` from the previous frame instead of stopping projection, eliminating "model flickering" in real-time scenarios.  
   - **Semi-Transparent Faces (`AR_cube.py`)**: The logic of `addWeighted(overlay, 0.6, frame, 0.4, 0)` balances the visibility of the AR model and the clarity of the background, avoiding "model occlusion of key chessboard corners" (which would invalidate subsequent detection).  
   - **Model Preprocessing (`AR_cat.py`)**: Without centering, the cat model would deviate from the chessboard; without Z-alignment, the model would float in the air—both issues are resolved by the `load_3d_model()` function.  

2. **Correlation Between Calibration Error and AR Quality**:  
From `code.py`, the mean reprojection error is approximately 0.1083 pixels, which directly determines AR accuracy:  
- If the error exceeds 2 pixels, the cube/cat model would be misaligned (e.g., cube edges not parallel to the chessboard grid).  
- The consistency between the error value and AR alignment proves that the calibration parameters used in all AR code are reliable.  


### 1.5 Experiment Conclusion
1. **Task Completion**:  
   - **Task 3**: `check_pointcloud.py` successfully visualizes the camera-chessboard system, with good spatial consistency between camera centers and the chessboard point cloud—verifying the accuracy of extrinsic parameters.  
   - **Task 4**: `code.py` and `AR_cat.py` realize stable AR projection for both simple (cube) and complex (cat) models. The models align with the chessboard, proving that calibration parameters can be applied to practical AR scenarios.  

2. **Key Takeaway**:  
All results rely on the **consistency of parameters and logic** across code files. This consistency ensures that calibration results are reusable, and AR/PLY tasks can be completed without re-collecting data—highlighting the advantages of the modular design of the provided code.  

## 2. Bonus Part
Bonus part results are presented in Section 1.3.2 Task 4 & Bonus: AR Projection# 1.Basic Part

