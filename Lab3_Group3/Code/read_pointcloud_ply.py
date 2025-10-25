import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

def read_ply_file(ply_path):
    """
    读取PLY文件，提取点坐标和颜色信息
    :param ply_path: PLY文件路径
    :return: points (N,3) 点坐标数组, colors (N,3) 颜色数组（0-255）
    """
    if not os.path.exists(ply_path):
        raise FileNotFoundError(f"PLY文件不存在：{ply_path}")
    
    points = []
    colors = []
    with open(ply_path, 'r') as f:
        lines = f.readlines()
        header_end_idx = lines.index("end_header\n")  # 找到文件头结束位置
        vertex_start_idx = header_end_idx + 1  # 点数据开始行
        
        # 解析文件头，获取点数量（可选，用于校验）
        for line in lines[:header_end_idx]:
            if line.startswith("element vertex"):
                vertex_count = int(line.strip().split()[-1])
                print(f"PLY文件中包含 {vertex_count} 个3D点")
        
        # 读取点坐标和颜色
        for line in lines[vertex_start_idx:]:
            line = line.strip()
            if not line:
                continue
            # PLY每行格式：x y z red green blue
            parts = list(map(float, line.split()))
            x, y, z = parts[:3]
            r, g, b = map(int, parts[3:6])
            points.append([x, y, z])
            colors.append([r/255.0, g/255.0, b/255.0])  # 转为0-1浮点数（matplotlib颜色格式）
    
    # 转为numpy数组
    points = np.array(points, dtype=np.float32)
    colors = np.array(colors, dtype=np.float32)
    
    # 区分棋盘格点（红色）和相机中心点（蓝色）
    chessboard_mask = (colors[:, 0] == 1.0) & (colors[:, 1] == 0.0) & (colors[:, 2] == 0.0)
    camera_mask = (colors[:, 0] == 0.0) & (colors[:, 1] == 0.0) & (colors[:, 2] == 1.0)
    chessboard_points = points[chessboard_mask]
    camera_points = points[camera_mask]
    
    print(f"其中：棋盘格角点 {len(chessboard_points)} 个，相机中心点 {len(camera_points)} 个")
    return chessboard_points, camera_points

def visualize_ply(chessboard_points, camera_points):
    """
    3D可视化PLY文件中的点云
    :param chessboard_points: (N,3) 棋盘格角点坐标
    :param camera_points: (M,3) 相机中心点坐标
    """
    # 创建3D图
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # 绘制棋盘格点（红色，较大点 size=50）
    ax.scatter(
        chessboard_points[:, 0], chessboard_points[:, 1], chessboard_points[:, 2],
        c='red', s=50, alpha=0.8, label=f'Chessboard Corners ({len(chessboard_points)} points)'
    )
    
    # 绘制相机中心点（蓝色，更大点 size=100，带边缘）
    ax.scatter(
        camera_points[:, 0], camera_points[:, 1], camera_points[:, 2],
        c='blue', s=100, edgecolors='white', linewidth=1.5, alpha=0.9,
        label=f'Camera Centers ({len(camera_points)} points)'
    )
    
    # 设置坐标轴标签（与原标定尺寸单位一致，默认mm）
    ax.set_xlabel('X Axis (mm)', fontsize=12)
    ax.set_ylabel('Y Axis (mm)', fontsize=12)
    ax.set_zlabel('Z Axis (mm)', fontsize=12)
    
    # 设置标题和图例
    ax.set_title('3D Visualization of Chessboard Corners and Camera Centers', fontsize=14, pad=20)
    ax.legend(fontsize=10, loc='upper right')
    
    # 调整视角（可根据需求修改elev和azim）
    ax.view_init(elev=30, azim=45)  # elev：仰角，azim：方位角
    
    # 显示网格
    ax.grid(True, alpha=0.3)
    
    # 显示图像
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # 配置PLY文件路径（需与生成时的output_ply一致）
    ply_path = "Calibration_Results/camera_chessboard_3d.ply"
    
    try:
        # 读取PLY文件，区分棋盘格点和相机中心
        chessboard_points, camera_points = read_ply_file(ply_path)
        
        # 3D可视化
        visualize_ply(chessboard_points, camera_points)
        
    except Exception as e:
        print(f"运行出错：{str(e)}")
        print("请检查：1. PLY文件路径是否正确；2. PLY文件格式是否正常（由之前的generate_ply.py生成）")