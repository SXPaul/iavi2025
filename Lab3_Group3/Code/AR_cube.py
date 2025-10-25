import os
import cv2
import numpy as np

chessboard_size = (11,8)  
square_size = 14.5   

calibration_file = "Calibration_Results/calibration_params.npz"

cube_size = 50        
cube_position = np.array([4*square_size, 3*square_size, 0])  
face_colors = [
    (255, 0, 0),     
    (0, 255, 0),     
    (0, 0, 255),     
    (255, 255, 0),  
    (255, 0, 255),   
    (0, 255, 255)   
]


def load_calibration_params(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"file doesn't exists: {file_path}")
    
    data = np.load(file_path)
    return data["mtx"], data["dist"] 


def define_colored_cube(size, position):
    half = size / 2
    vertices = np.array([
        [-half, -half, half],
        [half, -half, half],
        [half, half, half],
        [-half, half, half],
        [-half, -half, -half],
        [half, -half, -half],
        [half, half, -half],
        [-half, half, -half]
    ], dtype=np.float32)
    
    vertices += position
    
    faces = [
        [0, 1, 2, 3],  
        [4, 5, 6, 7],  
        [0, 3, 7, 4],  
        [1, 2, 6, 5], 
        [3, 2, 6, 7],  
        [0, 1, 5, 4]  
    ]
    
    return vertices, faces

def ar_cube_projection():
    mtx, dist = load_calibration_params(calibration_file)
    cube_vertices, cube_faces = define_colored_cube(cube_size, cube_position)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise IOError("can't open camera")
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    prev_rvec = None
    prev_tvec = None
    print("begin project,press 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        ret, corners = cv2.findChessboardCorners(
            gray, chessboard_size,
            flags=cv2.CALIB_CB_ADAPTIVE_THRESH +  
            cv2.CALIB_CB_FAST_CHECK +            
            cv2.CALIB_CB_NORMALIZE_IMAGE         
        )
        
        if ret:
            corners_refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1),
                criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            
            objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
            objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
            objp *= square_size
            
            _, rvec, tvec = cv2.solvePnP(objp, corners_refined, mtx, dist)
            prev_rvec, prev_tvec = rvec, tvec 
        
        else:
            if prev_rvec is not None and prev_tvec is not None:
                rvec, tvec = prev_rvec, prev_tvec
            else:
                cv2.putText(frame, "No checkerboard was detected", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow("Color cube AR projection", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue
        
        cube_2d, _ = cv2.projectPoints(cube_vertices, rvec, tvec, mtx, dist)
        cube_2d = cube_2d.reshape(-1, 2).astype(int)
        
        for i, face in enumerate(cube_faces):
            pts = cube_2d[face].reshape((-1, 1, 2))
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], face_colors[i])
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
            cv2.polylines(frame, [pts], isClosed=True, color=(255, 255, 255), thickness=2)
        
        cv2.imshow("Color cube AR projection", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        ar_cube_projection()
    except Exception as e:
        print(f"error: {str(e)}")