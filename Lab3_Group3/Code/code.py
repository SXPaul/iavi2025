import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from glob import glob

chessboard_size = (11, 8)  # (columns, rows)
square_size = 14.5  
image_dir = "../Data/images" 
output_dir = "Calibration_Results"  
os.makedirs(output_dir, exist_ok=True)

def load_images_and_detect_corners(image_dir, chessboard_size):
    image_paths = glob(os.path.join(image_dir, "*.bmp"))
    if not image_paths:
        raise ValueError(f"No bmp images found in {image_dir}, please check the path")
    
    obj_points = []  # World coordinates
    img_points = []  # Image coordinates
    objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
    objp *= square_size
    
    images = []
    valid_indices = []
    print(f"Starting to detect corners in {len(image_paths)} images...")
    for i, path in enumerate(image_paths):
        img = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        images.append(img)
        
        ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)
        if ret:
            valid_indices.append(i)
            obj_points.append(objp)
            corners_refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1),
                criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            img_points.append(corners_refined)
            
            img_with_corners = cv2.drawChessboardCorners(img.copy(), chessboard_size, corners_refined, ret)
            save_path = os.path.join(output_dir, f"corners_detected_{i}.png")
            cv2.imwrite(save_path, img_with_corners)
            print(f"Image {i+1}/{len(image_paths)}: Corner detection successful")
        else:
            print(f"Image {i+1}/{len(image_paths)}: Corner detection failed")
    
    if len(valid_indices) < 5:
        raise Warning("Fewer than 5 valid images, calibration may be unreliable")
    return images, obj_points, img_points, valid_indices, image_paths

def calibrate_camera(obj_points, img_points, image_shape):
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, image_shape[::-1], None, None
    )
    
    # Calculate mean reprojection error
    mean_error = 0
    for i in range(len(obj_points)):
        img_points_reproj, _ = cv2.projectPoints(obj_points[i], rvecs[i], tvecs[i], mtx, dist)
        error = cv2.norm(img_points[i], img_points_reproj, cv2.NORM_L2) / len(img_points_reproj)
        mean_error += error
    mean_error /= len(obj_points)
    
    print(f"\nCalibration completed! Mean reprojection error: {mean_error:.4f} pixels")
    print(f"Intrinsic matrix:\n{mtx}")
    np.savez(
        os.path.join(output_dir, "calibration_params.npz"),
        mtx=mtx, dist=dist, rvecs=rvecs, tvecs=tvecs, mean_error=mean_error
    )
    return mtx, dist, rvecs, tvecs, mean_error

def project_cube_to_image(images, valid_indices, mtx, dist, rvecs, tvecs):
    cube_size = square_size * 2  
    cube_3d = np.array([
        [0, 0, 0], [cube_size, 0, 0], [cube_size, cube_size, 0], [0, cube_size, 0],
        [0, 0, cube_size], [cube_size, 0, cube_size], [cube_size, cube_size, cube_size], [0, cube_size, cube_size]
    ], dtype=np.float32)
    
    #  6 cube faces and  they are defined as different colors to check whether the project is right
    cube_faces = [
        ([0, 1, 2, 3], (255, 0, 0)),   
        ([4, 5, 6, 7], (0, 255, 0)),    
        ([0, 1, 5, 4], (0, 0, 255)),   
        ([2, 3, 7, 6], (255, 255, 0)), 
        ([0, 3, 7, 4], (255, 0, 255)),  
        ([1, 2, 6, 5], (0, 255, 255))   
    ]
    
    cube_edges = [
        (0, 1), (1, 2), (2, 3), (3, 0), 
        (4, 5), (5, 6), (6, 7), (7, 4),  
        (0, 4), (1, 5), (2, 6), (3, 7)   
    ]
    
    # Project cube
    for i in range(min(3, len(valid_indices))):
        img_idx = valid_indices[i]
        img = images[img_idx].copy()
        rvec = rvecs[i]  
        tvec = tvecs[i] 
        # Undistort the image 
        h, w = img.shape[:2]
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
        undistorted_img = cv2.undistort(img, mtx, dist, None, newcameramtx)
        x_roi, y_roi, w_roi, h_roi = roi
        undistorted_img = undistorted_img[y_roi:y_roi+h_roi, x_roi:x_roi+w_roi]
        
        # Project 3D cube vertices to 2D pixel coordinates
        cube_2d, _ = cv2.projectPoints(cube_3d, rvec, tvec, mtx, dist)
        cube_2d = cube_2d.reshape(-1, 2).astype(int)  
        
        cube_2d[:, 0] -= x_roi  
        cube_2d[:, 1] -= y_roi  
        
        color_layer = undistorted_img.copy()
        for face_vertices_idx, face_color in cube_faces:
            face_2d = cube_2d[face_vertices_idx].reshape(1, -1, 2)  
            cv2.fillConvexPoly(color_layer, face_2d, face_color)
        
        undistorted_with_faces = cv2.addWeighted(color_layer, 0.5, undistorted_img, 0.5, 0)
        
        for (p1_idx, p2_idx) in cube_edges:
            p1 = tuple(cube_2d[p1_idx])
            p2 = tuple(cube_2d[p2_idx])
            cv2.line(undistorted_with_faces, p1, p2, (255, 255, 255), 2)  # White edge, 2px thick
        
        # Save the final image
        save_path = os.path.join(output_dir, f"undistorted_with_colored_cube_{i}.png")
        cv2.imwrite(save_path, undistorted_with_faces)
        print(f"Image with colored cube saved: {save_path}")


def visualize_results(images, valid_indices, mtx, dist, image_paths, rvecs, tvecs):
    # Chessboard visualization
    first_valid_idx = valid_indices[0]
    chessboard_vis = images[first_valid_idx].copy()
    cv2.putText(
        chessboard_vis, f"Chessboard ({chessboard_size[0]}x{chessboard_size[1]} corners)",
        (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
    )
    cv2.imwrite(os.path.join(output_dir, "chessboard_visualization.png"), chessboard_vis)
    
    # Camera positions visualization
    num_vis = min(5, len(valid_indices))
    vis_indices = np.linspace(0, len(valid_indices)-1, num_vis, dtype=int)
    vis_images = [images[valid_indices[i]] for i in vis_indices]
    vis_resized = [cv2.resize(img, (400, 300)) for img in vis_images]
    stitched_img = np.hstack(vis_resized)
    cv2.putText(
        stitched_img, "Camera Positions (Different Angles/Coverages)",
        (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2
    )
    cv2.imwrite(os.path.join(output_dir, "camera_positions_visualization.png"), stitched_img)
    
    # Original vs undistorted comparison
    for i in range(min(3, len(valid_indices))):
        idx = valid_indices[i]
        img = images[idx]
        h, w = img.shape[:2]
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
        undistorted = cv2.undistort(img, mtx, dist, None, newcameramtx)
        x_roi, y_roi, w_roi, h_roi = roi
        undistorted = undistorted[y_roi:y_roi+h_roi, x_roi:x_roi+w_roi]
        
        img_resized = cv2.resize(img, (600, 400))
        undistorted_resized = cv2.resize(undistorted, (600, 400))
        cv2.putText(img_resized, "Original Image", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(undistorted_resized, "Undistorted Image", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        comparison_img = np.vstack([img_resized, undistorted_resized])
        cv2.imwrite(os.path.join(output_dir, f"original_vs_undistorted_{i}.png"), comparison_img)
    
    project_cube_to_image(images, valid_indices, mtx, dist, rvecs, tvecs)
    print("\nAll visualizations completed (including colored cube)")


if __name__ == "__main__":
    try:
        # Load images and detect corners
        images, obj_points, img_points, valid_indices, img_paths = load_images_and_detect_corners(
            image_dir, chessboard_size
        )
        
        # Camera calibration
        if valid_indices:
            image_shape = images[0].shape[:2]
            mtx, dist, rvecs, tvecs, mean_error = calibrate_camera(
                obj_points, img_points, image_shape
            )
            
            # Visualization (including colored cube)
            visualize_results(images, valid_indices, mtx, dist, img_paths, rvecs, tvecs)
            
            # Save calibration analysis
            with open(os.path.join(output_dir, "calibration_analysis.txt"), "w") as f:
                f.write("Analysis of factors affecting calibration quality:\n\n")
                f.write(f"1. Number of images: {len(valid_indices)} valid images (need >5)\n")
                f.write("2. Coverage: Chessboard must cover image edges\n")
                f.write("3. View angles: Multiple angles improve robustness\n")
                f.write("4. Other factors: Chessboard accuracy, lighting, camera stability\n")
                f.write(f"Mean reprojection error: {mean_error:.4f} pixels (<1 is good)\n")
        
    except Exception as e:
        print("Error:", str(e))