import os
import cv2
import numpy as np
import open3d as o3d
from glob import glob

# -------------------------- 配置参数 --------------------------
# 棋盘格参数（需与标定程序一致）
chessboard_size = (9, 6)  # 内角点行列数
square_size = 20  # 棋盘格边长(mm)

# 标定参数文件路径（之前生成的内参和畸变系数）
calibration_file = "Calibration_Results/calibration_params.npz"

# PLY模型路径（当前文件夹下的cat.ply）
model_path = "cat.ply"

# 模型缩放与位置调整（根据实际效果微调）
model_scale = 300  # 模型缩放比例（mm）
model_offset = np.array([4*square_size, 3*square_size, 0])  # 模型在棋盘格上的偏移（中心位置）


# -------------------------- 加载标定参数 --------------------------
def load_calibration_params(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到标定文件: {file_path}，请先运行相机标定程序")
    
    data = np.load(file_path)
    return data["mtx"], data["dist"]  # 内参矩阵和畸变系数


# -------------------------- 加载并预处理3D模型 --------------------------
def load_3d_model(path, scale=1.0, offset=np.array([0, 0, 0])):
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到模型文件: {path}")
    
    # 加载PLY模型
    mesh = o3d.io.read_triangle_mesh(path)
    if not mesh.has_vertices():
        raise ValueError("模型文件不包含顶点数据")
    
    # 模型预处理：居中、缩放、平移
    vertices = np.asarray(mesh.vertices)
    # 1. 居中（将模型中心移至原点，保持形状对称）
    vertices_center = np.mean(vertices, axis=0)
    vertices = vertices - vertices_center
    # 2. 缩放（按设定比例放大/缩小模型）
    vertices = vertices * scale
    # 3. 关键：将模型底部对齐Z=0（让最低处刚好接触棋盘格平面）
    vertices_min_z = np.min(vertices[:, 2])  # 找到模型所有顶点的最低Z值
    vertices[:, 2] -= vertices_min_z        # 所有顶点Z值减去最低Z值→最低处Z=0
    # 4. 平移到棋盘格目标位置（offset的Z值可控制模型高度，设0即贴地）
    vertices = vertices + offset
    
    # 更新模型顶点
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    # 计算模型的三角形面（用于绘制）
    triangles = np.asarray(mesh.triangles)
    return vertices, triangles


# -------------------------- 实时AR投影主函数 --------------------------
def ar_realtime_projection():
    # 加载标定参数
    mtx, dist = load_calibration_params(calibration_file)
    # 加载3D模型（顶点和三角形面）
    model_vertices, model_triangles = load_3d_model(
        model_path, 
        scale=model_scale, 
        offset=model_offset
    )
    
    # 打开摄像头（0为默认摄像头）
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise IOError("无法打开摄像头")
    
    print("开始实时AR投影（按 'q' 退出）...")
    while True:
        # 读取一帧图像
        ret, frame = cap.read()
        if not ret:
            break
        
        # 转换为灰度图，检测棋盘格角点
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)
        
        if ret:
            # 亚像素级角点优化
            corners_refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1),
                criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            
            # 生成棋盘格世界坐标系（Z=0）
            objp = np.zeros((chessboard_size[0]*chessboard_size[1], 3), np.float32)
            objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
            objp *= square_size
            
            # 求解外参（旋转向量rvec和平移向量tvec）
            _, rvec, tvec = cv2.solvePnP(
                objp, corners_refined, mtx, dist, 
                flags=cv2.SOLVEPNP_ITERATIVE
            )
            
            # 将3D模型顶点投影到2D图像平面
            model_vertices_2d, _ = cv2.projectPoints(
                model_vertices, rvec, tvec, mtx, dist
            )
            model_vertices_2d = model_vertices_2d.reshape(-1, 2).astype(int)  # 转换为整数像素坐标
            
            # 绘制3D模型的三角形面（填充颜色）
            for triangle in model_triangles:
                # 获取三角形的三个顶点（2D坐标）
                p1 = tuple(model_vertices_2d[triangle[0]])
                p2 = tuple(model_vertices_2d[triangle[1]])
                p3 = tuple(model_vertices_2d[triangle[2]])
                # 随机生成面颜色（增加视觉效果）
                color=(147, 20, 255)
                # 填充三角形
                cv2.fillConvexPoly(frame, np.array([p1, p2, p3]), color)
                # 绘制三角形边缘（黑色描边）
                cv2.line(frame, p1, p2, (255,255,255), 1)
                cv2.line(frame, p2, p3, (255,255,255), 1)
                cv2.line(frame, p3, p1, (255,255,255), 1)
        
        # 显示结果
        cv2.imshow("AR Cat Projection", frame)
        
        # 按 'q' 退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()


# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    try:
        ar_realtime_projection()
    except Exception as e:
        print("错误:", str(e))

'''
### 程序功能说明
1. **核心原理**：  
   通过实时检测棋盘格的位置，计算相机与棋盘格的相对位姿（外参），再利用相机内参将3D猫模型的顶点投影到2D图像平面，最终绘制出模型的三角形面，实现“虚拟猫模型叠加在真实棋盘格上”的AR效果。

2. **关键步骤**：  
   - 加载相机内参和畸变系数（来自之前的标定结果）；  
   - 用Open3D读取`cat.ply`模型，进行缩放、平移等预处理（使其适配棋盘格大小）；  
   - 实时摄像头采集画面，检测棋盘格角点并计算外参；  
   - 将3D模型顶点投影到2D图像，通过填充三角形面绘制模型。

3. **参数调整**：  
   - 若模型过大/过小，修改`model_scale`（增大/减小缩放比例）；  
   - 若模型位置偏移，调整`model_offset`（前两个值控制在棋盘格上的XY位置，第三个值控制高度）；  
   - 若投影抖动，可增加`cv2.findChessboardCorners`的检测精度（如调整亚像素窗口大小）。


### 使用前准备
1. 确保已安装Open3D：`pip install open3d`；  
2. 确保`cat.ply`文件在程序运行目录下；  
3. 确保之前的标定程序已生成`Calibration_Results/calibration_params.npz`文件；  
4. 准备好棋盘格，运行程序后将其置于摄像头前，模型会自动投影到棋盘格上，移动棋盘格或相机，模型会跟随视角变化。

运行程序后，你将看到猫模型实时叠加在真实棋盘格上，实现动态AR效果。按`q`键退出程序。
'''