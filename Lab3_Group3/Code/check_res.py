import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# -------------------------- 配置参数 --------------------------
# 标定结果文件路径（与之前生成的calibration_params.npz对应）
calibration_file = "Calibration_Results/calibration_params.npz"
# 散点图保存路径
output_dir = "Calibration_Plots"
os.makedirs(output_dir, exist_ok=True)


# -------------------------- 加载标定数据 --------------------------
def load_calibration_data(file_path):
    """加载标定参数文件，返回关键参数"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到标定文件: {file_path}，请先运行相机标定程序")
    
    data = np.load(file_path)
    return {
        "mtx": data["mtx"],  # 内参矩阵
        "dist": data["dist"],  # 畸变系数
        "rvecs": data["rvecs"],  # 旋转向量列表（每个图像对应一个）
        "tvecs": data["tvecs"],  # 平移向量列表（每个图像对应一个）
        "mean_error": data["mean_error"]  # 平均重投影误差
    }


# -------------------------- 计算单张图像的重投影误差 --------------------------
def calculate_per_image_errors(calib_data, obj_points, img_points):
    """计算每张图像的重投影误差（需加载角点数据）"""
    mtx = calib_data["mtx"]
    dist = calib_data["dist"]
    rvecs = calib_data["rvecs"]
    tvecs = calib_data["tvecs"]
    
    per_image_errors = []
    for i in range(len(obj_points)):
        # 投影3D点到2D图像
        img_points_reproj, _ = cv2.projectPoints(
            obj_points[i], rvecs[i], tvecs[i], mtx, dist
        )
        # 计算当前图像的平均误差
        error = cv2.norm(img_points[i], img_points_reproj, cv2.NORM_L2) / len(img_points_reproj)
        per_image_errors.append(error)
    
    return np.array(per_image_errors)


# -------------------------- 散点图可视化函数 --------------------------
def plot_reprojection_errors(errors):
    """绘制每张图像的重投影误差散点图"""
    plt.figure(figsize=(10, 6))
    # 散点图：x轴为图像索引，y轴为误差值
    plt.scatter(range(len(errors)), errors, color='red', alpha=0.7, label='Per-image error')
    # 水平线：平均误差
    plt.axhline(y=np.mean(errors), color='blue', linestyle='--', label=f'Mean error: {np.mean(errors):.4f}')
    plt.xlabel('Image Index')
    plt.ylabel('Reprojection Error (pixels)')
    plt.title('Reprojection Error Distribution Across Images')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    save_path = os.path.join(output_dir, "reprojection_errors_scatter.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"重投影误差散点图已保存至: {save_path}")
    plt.close()


def plot_rotation_vectors(rvecs):
    """绘制旋转向量（rvecs）的3D散点图（x/y/z分量分布）"""
    # 转换旋转向量为numpy数组（shape: [N, 3]）
    rvecs_np = np.array(rvecs).reshape(-1, 3)
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    # 3D散点：每个点代表一个图像的旋转向量（x,y,z）
    scatter = ax.scatter(
        rvecs_np[:, 0], rvecs_np[:, 1], rvecs_np[:, 2],
        c=range(len(rvecs_np)),  # 用颜色区分不同图像
        cmap='viridis', alpha=0.8, s=50
    )
    ax.set_xlabel('Rotation X (rad)')
    ax.set_ylabel('Rotation Y (rad)')
    ax.set_zlabel('Rotation Z (rad)')
    ax.set_title('3D Distribution of Rotation Vectors (rvecs)')
    fig.colorbar(scatter, label='Image Index')
    save_path = os.path.join(output_dir, "rotation_vectors_3d.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"旋转向量3D散点图已保存至: {save_path}")
    plt.close()


def plot_translation_vectors(tvecs):
    """绘制平移向量（tvecs）的3D散点图（x/y/z分量分布）"""
    # 转换平移向量为numpy数组（shape: [N, 3]）
    tvecs_np = np.array(tvecs).reshape(-1, 3)
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    # 3D散点：每个点代表一个图像的平移向量（x,y,z）
    scatter = ax.scatter(
        tvecs_np[:, 0], tvecs_np[:, 1], tvecs_np[:, 2],
        c=range(len(tvecs_np)),  # 用颜色区分不同图像
        cmap='plasma', alpha=0.8, s=50
    )
    ax.set_xlabel('Translation X (mm)')
    ax.set_ylabel('Translation Y (mm)')
    ax.set_zlabel('Translation Z (mm)')
    ax.set_title('3D Distribution of Translation Vectors (tvecs)')
    fig.colorbar(scatter, label='Image Index')
    save_path = os.path.join(output_dir, "translation_vectors_3d.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"平移向量3D散点图已保存至: {save_path}")
    plt.close()


def plot_distortion_coefficients(dist):
    """绘制畸变系数的条形散点图（k1, k2, p1, p2, k3）"""
    # 畸变系数通常为 [k1, k2, p1, p2, k3]
    dist_coeffs = dist.flatten()[:5]  # 取前5个关键系数
    labels = ['k1 (Radial)', 'k2 (Radial)', 'p1 (Tangential)', 'p2 (Tangential)', 'k3 (Radial)']
    
    plt.figure(figsize=(10, 6))
    # 条形散点：每个畸变系数的值
    plt.scatter(labels, dist_coeffs, color='green', s=100, alpha=0.7)
    # 水平线：零点（理想值）
    plt.axhline(y=0, color='red', linestyle='--', label='Ideal value (0)')
    plt.xlabel('Distortion Coefficients')
    plt.ylabel('Value')
    plt.title('Distribution of Distortion Coefficients')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.legend()
    save_path = os.path.join(output_dir, "distortion_coefficients.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"畸变系数散点图已保存至: {save_path}")
    plt.close()


# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    try:
        # 加载标定数据
        calib_data = load_calibration_data(calibration_file)
        print("成功加载标定数据，开始绘制散点图...")
        
        # 1. 绘制畸变系数散点图
        plot_distortion_coefficients(calib_data["dist"])
        
        # 2. 绘制旋转向量3D散点图
        plot_rotation_vectors(calib_data["rvecs"])
        
        # 3. 绘制平移向量3D散点图
        plot_translation_vectors(calib_data["tvecs"])
        
        # 4. 绘制重投影误差散点图（需要重新加载角点数据）
        # 重新调用角点检测函数获取obj_points和img_points
        from glob import glob
        import cv2
        
        # 棋盘格参数（需与标定程序一致）
        chessboard_size = (9, 6)
        square_size = 20
        image_dir = "../Data/images"
        
        # 重新加载图像和角点数据（仅为计算单张图像误差）
        image_paths = glob(os.path.join(image_dir, "*.bmp"))
        obj_points = []
        img_points = []
        objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
        objp *= square_size
        
        for path in image_paths:
            img = cv2.imread(path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)
            if ret:
                obj_points.append(objp)
                corners_refined = cv2.cornerSubPix(
                    gray, corners, (11, 11), (-1, -1),
                    criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                )
                img_points.append(corners_refined)
        
        # 计算每张图像的重投影误差并绘图
        per_image_errors = calculate_per_image_errors(calib_data, obj_points, img_points)
        plot_reprojection_errors(per_image_errors)
        
        print("\n所有散点图绘制完成，保存至目录: ", output_dir)
        
    except Exception as e:
        print("错误:", str(e))