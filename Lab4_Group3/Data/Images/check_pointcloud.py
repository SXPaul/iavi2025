import os
import numpy as np
import open3d as o3d
import cv2
from glob import glob

# -------------------------- 配置参数 --------------------------
chessboard_size = (11, 8)  # 内角点行列数
square_size = 14.5  # 棋盘格边长(mm)
calibration_file = "Calibration_Results/calibration_params.npz"
image_dir = "../Data/images"
camera_size = 50          # 相机模型大小
point_size = 5            # 棋盘点大小
chessboard_color = [0, 1, 0]  # 棋盘格点云颜色（绿色）
camera_color = [1, 0, 0]      # 相机模型颜色（红色）


# -------------------------- 加载数据 --------------------------
def load_calibration_data():
    if not os.path.exists(calibration_file):
        raise FileNotFoundError(f"未找到标定文件: {calibration_file}")
    
    data = np.load(calibration_file)
    return {
        "mtx": data["mtx"],
        "dist": data["dist"],
        "rvecs": data["rvecs"],
        "tvecs": data["tvecs"]
    }


def get_chessboard_points():
    objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
    objp *= square_size
    return objp


def get_valid_image_count(calib_data):
    return len(calib_data["rvecs"])


# -------------------------- 转换位姿为Open3D格式（核心修正） --------------------------
def rotation_vector_to_matrix(rvec):
    """将旋转向量转换为旋转矩阵，并修正维度"""
    # 确保旋转向量是三维的
    rvec = rvec.flatten()[:3]  # 关键修正：展平并取前3个元素
    R, _ = cv2.Rodrigues(rvec)
    return R.astype(np.float64)  # 确保精度


def create_camera_actor(pose_matrix, size=camera_size):
    center = pose_matrix[:3, 3]
    
    # 提取轴方向并修正维度
    x_axis = pose_matrix[:3, 0].flatten() * size  # 关键修正：展平数组
    y_axis = pose_matrix[:3, 1].flatten() * size
    z_axis = pose_matrix[:3, 2].flatten() * size
    
    camera_front = center - z_axis * 0.5
    
    # 视锥体参数
    fov = 60
    half_fov = np.radians(fov / 2)
    far = size * 0.8
    top = far * np.tan(half_fov)
    right = top * 1.6
    
    # 视锥体顶点
    p1 = camera_front - z_axis * far + y_axis * top + x_axis * right
    p2 = camera_front - z_axis * far + y_axis * top - x_axis * right
    p3 = camera_front - z_axis * far - y_axis * top - x_axis * right
    p4 = camera_front - z_axis * far - y_axis * top + x_axis * right
    
    # 线段集合
    lines = [
        [center, center + x_axis],
        [center, center + y_axis],
        [center, center + z_axis],
        [camera_front, p1], [camera_front, p2],
        [camera_front, p3], [camera_front, p4],
        [p1, p2], [p2, p3], [p3, p4], [p4, p1]
    ]
    
    # 确保所有点都是三维的
    lines = [[p.flatten()[:3] for p in line] for line in lines]  # 关键修正
    
    colors = [camera_color for _ in range(len(lines))]
    
    line_set = o3d.geometry.LineSet()
    line_set.points = o3d.utility.Vector3dVector(np.vstack(lines))
    line_set.lines = o3d.utility.Vector2iVector(
        [[i*2, i*2+1] for i in range(len(lines))]
    )
    line_set.colors = o3d.utility.Vector3dVector(colors)
    return line_set


# -------------------------- 主可视化函数 --------------------------
def visualize_camera_and_chessboard():
    calib_data = load_calibration_data()
    chessboard_points = get_chessboard_points()
    num_images = get_valid_image_count(calib_data)
    
    # 棋盘格点云
    chessboard_pcd = o3d.geometry.PointCloud()
    chessboard_pcd.points = o3d.utility.Vector3dVector(chessboard_points.astype(np.float64))
    chessboard_pcd.paint_uniform_color(chessboard_color)
    
    # 相机模型
    camera_actors = []
    for i in range(num_images):
        rvec = calib_data["rvecs"][i]
        tvec = calib_data["tvecs"][i].flatten()[:3]  # 修正平移向量维度
        
        R = rotation_vector_to_matrix(rvec)
        pose_matrix = np.eye(4, dtype=np.float64)
        pose_matrix[:3, :3] = R.T
        pose_matrix[:3, 3] = -R.T @ tvec  # 修正矩阵乘法维度
        
        camera_actor = create_camera_actor(pose_matrix)
        camera_actors.append(camera_actor)
    
    # 世界坐标系
    axes = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=100, origin=[0, 0, 0]
    )
    
    # 可视化
    visualizer = o3d.visualization.Visualizer()
    visualizer.create_window(window_name="相机与棋盘格点云可视化")
    
    visualizer.add_geometry(chessboard_pcd)
    visualizer.add_geometry(axes)
    for cam in camera_actors:
        visualizer.add_geometry(cam)
    
    opt = visualizer.get_render_option()
    opt.background_color = [1, 1, 1]
    opt.point_size = point_size
    
    visualizer.run()
    visualizer.destroy_window()


if __name__ == "__main__":
    try:
        visualize_camera_and_chessboard()
        print("可视化完成")
    except Exception as e:
        print(f"错误: {str(e)}")