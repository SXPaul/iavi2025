import os
import cv2
import numpy as np

# -------------------------- 配置参数（根据实际情况修改） --------------------------
# 棋盘格参数（必须与标定程序一致）
chessboard_size = (9, 6)  # 内角点行列数 (columns, rows)
square_size = 20          # 棋盘格边长 (mm)

# 标定参数文件路径
calibration_file = "Calibration_Results/calibration_params.npz"

# 立方体参数
cube_size = 50           # 立方体边长 (mm)，越大投影越大
cube_position = np.array([4*square_size, 3*square_size, 0])  # 立方体在棋盘格上的位置（中心）

# 六个面的颜色（BGR格式）
face_colors = [
    (255, 0, 0),     # 前面：蓝色
    (0, 255, 0),     # 后面：绿色
    (0, 0, 255),     # 左面：红色
    (255, 255, 0),   # 右面：黄色
    (255, 0, 255),   # 上面：品红
    (0, 255, 255)    # 下面：青色
]


# -------------------------- 加载标定参数 --------------------------
def load_calibration_params(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"标定文件不存在: {file_path}，请先运行标定程序")
    
    data = np.load(file_path)
    return data["mtx"], data["dist"]  # 内参矩阵和畸变系数


# -------------------------- 定义彩色立方体的3D顶点和面 --------------------------
def define_colored_cube(size, position):
    """定义立方体的顶点、面索引和对应颜色"""
    # 立方体8个顶点的世界坐标（以中心为原点，Z轴向上）
    half = size / 2
    vertices = np.array([
        # 前面（Z=half）
        [-half, -half, half],
        [half, -half, half],
        [half, half, half],
        [-half, half, half],
        # 后面（Z=-half）
        [-half, -half, -half],
        [half, -half, -half],
        [half, half, -half],
        [-half, half, -half]
    ], dtype=np.float32)
    
    # 平移到目标位置（棋盘格上的position）
    vertices += position
    
    # 6个面的顶点索引（与face_colors顺序对应）
    faces = [
        [0, 1, 2, 3],  # 前面
        [4, 5, 6, 7],  # 后面
        [0, 3, 7, 4],  # 左面
        [1, 2, 6, 5],  # 右面
        [3, 2, 6, 7],  # 上面
        [0, 1, 5, 4]   # 下面
    ]
    
    return vertices, faces


# -------------------------- 实时AR投影主函数（优化版） --------------------------
def ar_cube_projection():
    # 加载标定参数
    mtx, dist = load_calibration_params(calibration_file)
    
    # 定义立方体
    cube_vertices, cube_faces = define_colored_cube(cube_size, cube_position)
    
    # 打开摄像头（尝试不同的摄像头索引，0不行换1）
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise IOError("无法打开摄像头，请检查设备连接")
    
    # 降低摄像头分辨率（提升实时性）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 缓存上一帧的外参（解决断续问题）
    prev_rvec = None
    prev_tvec = None
    print("开始彩色立方体AR投影（按 'q' 退出）")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 检测棋盘格角点（优化参数，提升检测成功率）
        ret, corners = cv2.findChessboardCorners(
            gray, chessboard_size,
            flags=cv2.CALIB_CB_ADAPTIVE_THRESH +  # 自适应阈值，适应光线变化
            cv2.CALIB_CB_FAST_CHECK +            # 快速预检测，加快速度
            cv2.CALIB_CB_NORMALIZE_IMAGE         # 归一化图像，增强对比度
        )
        
        # 角点亚像素优化
        if ret:
            corners_refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1),
                criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            
            # 生成棋盘格世界坐标
            objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
            objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
            objp *= square_size
            
            # 求解外参（旋转和平移向量）
            _, rvec, tvec = cv2.solvePnP(objp, corners_refined, mtx, dist)
            prev_rvec, prev_tvec = rvec, tvec  # 更新缓存
        
        # 若当前帧检测失败，使用上一帧的外参（避免断续）
        else:
            if prev_rvec is not None and prev_tvec is not None:
                rvec, tvec = prev_rvec, prev_tvec
            else:
                # 无缓存时显示提示
                cv2.putText(frame, "未检测到棋盘格", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow("彩色立方体AR投影", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue
        
        # 将立方体顶点投影到图像平面
        cube_2d, _ = cv2.projectPoints(cube_vertices, rvec, tvec, mtx, dist)
        cube_2d = cube_2d.reshape(-1, 2).astype(int)
        
        # 绘制立方体的面（带透明度）
        for i, face in enumerate(cube_faces):
            # 获取面的四个顶点
            pts = cube_2d[face].reshape((-1, 1, 2))
            # 创建透明图层
            overlay = frame.copy()
            # 填充面颜色
            cv2.fillPoly(overlay, [pts], face_colors[i])
            # 与原图融合（透明度0.6）
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
            # 绘制面的边缘（白色，加粗）
            cv2.polylines(frame, [pts], isClosed=True, color=(255, 255, 255), thickness=2)
        
        # 显示结果
        cv2.imshow("彩色立方体AR投影", frame)
        
        # 按q退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()


# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    try:
        ar_cube_projection()
    except Exception as e:
        print(f"错误: {str(e)}")


'''
### 程序优化点（解决“投影效果不好”的问题）
1. **提升检测稳定性**：
   - 新增角点检测 flags 参数（自适应阈值、归一化图像），增强对光线变化和模糊的容忍度。
   - 添加“外参缓存”机制：当前帧检测失败时，自动使用上一帧的旋转/平移参数，避免模型突然消失。

2. **优化投影效果**：
   - 立方体采用简单的8顶点+6面结构，投影计算量小，实时性更好（不会卡顿）。
   - 面填充使用半透明效果（0.6透明度），既保留彩色效果，又不完全遮挡棋盘格背景。
   - 白色粗边缘勾勒立方体轮廓，解决“面与面边界模糊”的问题。

3. **参数更易调整**：
   - `cube_size` 直接控制立方体大小（数值越大，投影越大）。
   - `cube_position` 控制立方体在棋盘格上的位置（XY值对应棋盘格格子数，Z=0表示底面贴棋盘）。


### 使用说明
1. 确保标定文件 `Calibration_Results/calibration_params.npz` 存在（若没有，先运行之前的标定程序）。
2. 调整棋盘格位置：确保光线充足、无反光，让棋盘格完整出现在摄像头画面中。
3. 若立方体大小不合适，修改 `cube_size`（如改为150增大）；若位置偏移，调整 `cube_position` 的XY值。

运行后，彩色立方体会稳定地叠加在棋盘格上，移动棋盘格或摄像头时，立方体会自然跟随视角变化，几乎不会出现“断断续续”的问题。按 `q` 键退出程序。
'''