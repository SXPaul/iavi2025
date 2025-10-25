import os
import numpy as np
import cv2


chessboard_size = (11, 8)  
square_size = 14.5      
npz_path = "Calibration_Results/calibration_params.npz"  
output_ply = "Calibration_Results/camera_chessboard_3d.ply" 


def generate_chessboard_points(chessboard_size, square_size):
    objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
    objp *= square_size
    
    return objp


def export_to_ply_from_npz(npz_path, chessboard_size, square_size, output_ply):
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Calibration parameter file not found: {npz_path}")
    
    data = np.load(npz_path)
    rvecs = data["rvecs"]  # Rotation vectors (list, each element shape=(3,1))
    tvecs = data["tvecs"]  # Translation vectors (list, each element shape=(3,1))

    chessboard_3d = generate_chessboard_points(chessboard_size, square_size)  # Shape: (N, 3)

    camera_centers = []  # List to store camera center coordinates (each element shape=(1,3))
    
    for rvec, tvec in zip(rvecs, tvecs):
        R, _ = cv2.Rodrigues(rvec)
        
        # Calculate camera center in world coordinate system: camera_center = -R^T * tvec
        # - R^T: Transpose of the rotation matrix
        # - Result shape is (3,1) (column vector), reshape to (1,3) (row vector) for consistency
        camera_center = (-R.T @ tvec).reshape(1, 3)
        camera_centers.append(camera_center)

    camera_centers = np.vstack(camera_centers)
    all_points = np.vstack([chessboard_3d, camera_centers])  # Shape: (N+M, 3)

    chessboard_colors = np.array([[255, 0, 0]] * len(chessboard_3d))
    camera_colors = np.array([[0, 0, 255]] * len(camera_centers))
    all_colors = np.vstack([chessboard_colors, camera_colors])

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