import os
import numpy as np
import cv2

# -----------------------------------------------------------------------------
# Configuration Parameters (MUST match the original camera calibration script)
# -----------------------------------------------------------------------------
chessboard_size = (11, 8)  # Number of chessboard corners (columns, rows)
square_size = 14.5         # Physical size of each chessboard square (unit: mm)
npz_path = "Calibration_Results/calibration_params.npz"  # Path to calibration parameters file
output_ply = "Calibration_Results/camera_chessboard_3d.ply"  # Path to output .ply file


def generate_chessboard_points(chessboard_size, square_size):
    """
    Generate 3D world coordinates of chessboard corners (consistent with the original calibration code).
    
    Parameters:
        chessboard_size (tuple): Number of inner corners of the chessboard (columns, rows)
        square_size (float): Physical size of each square on the chessboard (unit: mm)
    
    Returns:
        objp (np.ndarray): 3D coordinates of chessboard corners, shape=(N, 3) 
                           (N = columns * rows, Z-coordinate is 0 as the chessboard lies on X-Y plane)
    """
    # Initialize coordinate array: N rows (each corner), 3 columns (X, Y, Z)
    objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
    
    # Generate 2D grid coordinates (X, Y) using meshgrid, then reshape to (N, 2)
    # The grid starts from (0,0) (top-left corner of the chessboard)
    objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
    
    # Scale grid coordinates by square size to get real-world physical coordinates
    objp *= square_size
    
    return objp


def export_to_ply_from_npz(npz_path, chessboard_size, square_size, output_ply):
    """
    Export 3D coordinates of chessboard corners and camera centers to a .ply file,
    using calibration parameters stored in the .npz file.
    
    Parameters:
        npz_path (str): Path to the .npz file containing calibration parameters
        chessboard_size (tuple): Number of inner corners of the chessboard (columns, rows)
        square_size (float): Physical size of each square on the chessboard (unit: mm)
        output_ply (str): Path to save the generated .ply file
    
    Raises:
        FileNotFoundError: If the .npz calibration file does not exist
    """
    # 1. Load calibration parameters from .npz file
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Calibration parameter file not found: {npz_path}")
    
    # Load data from .npz file (extrinsic parameters are the core for camera center calculation)
    data = np.load(npz_path)
    rvecs = data["rvecs"]  # Rotation vectors (list, each element shape=(3,1))
    tvecs = data["tvecs"]  # Translation vectors (list, each element shape=(3,1))

    # 2. Generate 3D coordinates of chessboard corners (consistent with original calibration)
    chessboard_3d = generate_chessboard_points(chessboard_size, square_size)  # Shape: (N, 3)

    # 3. Calculate 3D coordinates of all camera centers
    camera_centers = []  # List to store camera center coordinates (each element shape=(1,3))
    
    # Iterate over each pair of rotation and translation vectors (one pair per calibration image)
    for rvec, tvec in zip(rvecs, tvecs):
        # Convert rotation vector to rotation matrix (shape: 3x3) using Rodrigues' transformation
        R, _ = cv2.Rodrigues(rvec)
        
        # Calculate camera center in world coordinate system: camera_center = -R^T * tvec
        # - R^T: Transpose of the rotation matrix
        # - Result shape is (3,1) (column vector), reshape to (1,3) (row vector) for consistency
        camera_center = (-R.T @ tvec).reshape(1, 3)
        
        camera_centers.append(camera_center)

    # 4. Concatenate chessboard points and camera center points
    # Convert camera centers list to a 2D array (shape: (M, 3), M = number of valid calibration images)
    camera_centers = np.vstack(camera_centers)
    
    # Concatenate chessboard points (N points) and camera centers (M points) into a single point cloud
    all_points = np.vstack([chessboard_3d, camera_centers])  # Shape: (N+M, 3)

    # 5. Assign colors to points (for clear visualization)
    # Red for chessboard corners (RGB: 255, 0, 0)
    chessboard_colors = np.array([[255, 0, 0]] * len(chessboard_3d))
    # Blue for camera centers (RGB: 0, 0, 255)
    camera_colors = np.array([[0, 0, 255]] * len(camera_centers))
    
    # Concatenate color arrays (consistent with the order of all_points)
    all_colors = np.vstack([chessboard_colors, camera_colors])

    # 6. Write point cloud data to .ply file (ASCII format)
    with open(output_ply, 'w') as f:
        # Write PLY file header (follow PLY format specification)
        f.write("ply\n")  # Magic number indicating PLY file
        f.write("format ascii 1.0\n")  # File format (ASCII) and version
        f.write(f"element vertex {len(all_points)}\n")  # Declare number of vertices (points)
        # Declare point attributes (X, Y, Z coordinates + RGB color)
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")  # End of header
        
        # Write each point's coordinates and color to the file
        for p, c in zip(all_points, all_colors):
            # Format: X Y Z R G B (coordinates保留2位小数, colors为整数)
            f.write(f"{p[0]:.2f} {p[1]:.2f} {p[2]:.2f} {int(c[0])} {int(c[1])} {int(c[2])}\n")

    print(f"PLY file generated successfully: {output_ply}")


if __name__ == "__main__":
    # Execute the main function to generate the .ply file
    export_to_ply_from_npz(npz_path, chessboard_size, square_size, output_ply)