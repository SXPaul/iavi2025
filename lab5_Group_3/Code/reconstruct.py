import os
import numpy as np
import cv2
from PIL import Image
import open3d as o3d


class GrayCodeReconstructor:
    def __init__(self, graycode_dir, captured_dir, width=1920, height=1080, nbits=11,
                 cam_dist=None, proj_dist=None):
        """
        Gray Code Reconstructor
        :param cam_dist: Camera distortion coefficients
        :param proj_dist: Projector distortion coefficients
        """
        self.graycode_dir = graycode_dir
        self.captured_dir = captured_dir
        self.width = width
        self.height = height
        self.nbits = nbits

        self.cam_dist = np.array(cam_dist, dtype=np.float64) if cam_dist is not None else np.zeros(5)
        self.proj_dist = np.array(proj_dist, dtype=np.float64) if proj_dist is not None else np.zeros(5)

        # Load reference images
        self.white_img = self._load_captured_image("reference_white.png")
        self.black_img = self._load_captured_image("reference_black.png")

        # Create mask
        self.mask = self._create_mask().astype(np.uint8)

        # Initialize mapping matrices
        self.x_map = np.zeros((self.height, self.width), dtype=np.int32)
        self.y_map = np.zeros((self.height, self.width), dtype=np.int32)

    # Internal utility functions
    def _load_image(self, path):
        """Load grayscale image"""
        img = Image.open(path).convert('L')
        return np.array(img, dtype=np.uint8)

    def _load_captured_image(self, img_name):
        """Load captured image"""
        captured_name = f"captured_{img_name}"
        path = os.path.join(self.captured_dir, captured_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Captured image not found: {path}")
        return self._load_image(path)

    def _create_mask(self):
        """Generate mask from white and black reference images"""
        diff = cv2.absdiff(self.white_img, self.black_img)
        _, mask = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        return (mask > 0).astype(np.uint8)

    def _gray_array_to_binary_array(self, g_array):
        """Convert Gray code array to binary code array"""
        g_array = g_array.astype(np.uint32)
        b = g_array.copy()
        shift = 1
        while True:
            shifted = (b >> shift).astype(np.uint32)   # Right shift b with explicit type conversion
            if not np.any(shifted):
                break
            b ^= shifted
            shift += 1
            if shift > 32:  # Safe exit to prevent infinite loop
                break
        return b

    # Gray code decoding
    def decode_graycode(self):
        print("Decoding Gray code patterns...")
        vertical_bits, horizontal_bits = [], []

        # Vertical direction (for projector x-coordinate)
        for bit in range(self.nbits):
            n = self._load_captured_image(f"graycode_bit{bit:02d}_vertical_normal.png")
            i = self._load_captured_image(f"graycode_bit{bit:02d}_vertical_inverted.png")
            diff = (n.astype(np.int16) - i.astype(np.int16))
            bitarr = ((diff > 0).astype(np.uint8)) * self.mask
            vertical_bits.append(bitarr)

        # Horizontal direction (for projector y-coordinate)
        for bit in range(self.nbits):
            n = self._load_captured_image(f"graycode_bit{bit:02d}_horizontal_normal.png")
            i = self._load_captured_image(f"graycode_bit{bit:02d}_horizontal_inverted.png")
            diff = (n.astype(np.int16) - i.astype(np.int16))
            bitarr = ((diff > 0).astype(np.uint8)) * self.mask
            horizontal_bits.append(bitarr)

        # Assemble integer Gray code values
        vb = np.stack(vertical_bits, axis=0).astype(np.uint32)
        hb = np.stack(horizontal_bits, axis=0).astype(np.uint32)

        g_vert = np.sum(vb << np.arange(self.nbits)[:, None, None], axis=0)
        g_hori = np.sum(hb << np.arange(self.nbits)[:, None, None], axis=0)

        # Convert to binary code
        print("Converting Gray code to binary...")
        b_vert = self._gray_array_to_binary_array(g_vert)
        b_hori = self._gray_array_to_binary_array(g_hori)

        # Normalize mapping to projector resolution
        max_val = (2 ** self.nbits) - 1  # Maximum original Gray code value (2^nbits - 1)
        # Calculate offsets
        voffset = ((1 << self.nbits) - self.width) // 2  # Vertical offset
        hoffset = ((1 << self.nbits) - self.height) // 2  # Horizontal offset

        # Subtract offsets from decoded binary values to get original projector coordinates (x: column, y: row)
        self.x_map = np.clip(b_vert - voffset, 0, self.width - 1).astype(np.int32)
        self.y_map = np.clip(b_hori - hoffset, 0, self.height - 1).astype(np.int32)
        print("Decoding completed")

    # Triangulation to generate point cloud
    def compute_point_cloud(self, cam_matrix, proj_matrix, R, T, output_ply="output.ply", keep_color=True):
        print("Starting triangulation...")

        ys, xs = np.where(self.mask == 1)
        if ys.size == 0:
            raise RuntimeError("Mask is empty, cannot generate point cloud")

        proj_xs = self.x_map[ys, xs]
        proj_ys = self.y_map[ys, xs]

        cam_pts = np.stack([xs, ys], axis=1).astype(np.float32).reshape(-1, 1, 2)
        proj_pts = np.stack([proj_xs, proj_ys], axis=1).astype(np.float32).reshape(-1, 1, 2)

        cam_pts_norm = cv2.undistortPoints(cam_pts, cam_matrix, self.cam_dist)
        proj_pts_norm = cv2.undistortPoints(proj_pts, proj_matrix, self.proj_dist)

        cam_pts_norm = cam_pts_norm.reshape(-1, 2)
        proj_pts_norm = proj_pts_norm.reshape(-1, 2)

        T = np.asarray(T).reshape(3, 1)
        P1 = np.hstack((np.eye(3), np.zeros((3, 1))))
        P2 = np.hstack((R, T))

        pts4d = cv2.triangulatePoints(P1.astype(np.float64), P2.astype(np.float64),
                                      cam_pts_norm.T.astype(np.float64), proj_pts_norm.T.astype(np.float64))

        w = pts4d[3, :]
        valid = np.abs(w) > 1e-8
        pts3d = np.zeros((pts4d.shape[1], 3), dtype=np.float64)
        pts3d[valid, :] = (pts4d[:3, valid] / w[valid]).T

        # Robust filtering
        finite_mask = np.isfinite(pts3d).all(axis=1) & (pts3d[:, 2] > 1e-6)
        valid_idx = np.where(valid & finite_mask)[0]
        if valid_idx.size == 0:
            raise RuntimeError("Triangulation failed, all points are invalid")

        pts3d = pts3d[valid_idx]
        xs_final = xs[valid_idx]
        ys_final = ys[valid_idx]

        # Color extraction
        colors = None
        if keep_color:
            try:
                ref_img = self._load_captured_image("reference_white.png")
                vals = ref_img[ys_final, xs_final]
                colors = np.stack([vals, vals, vals], axis=1).astype(np.uint8)
            except Exception:
                colors = None

        # Save point cloud
        os.makedirs(os.path.dirname(output_ply), exist_ok=True)
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pts3d)
        if colors is not None:
            pcd.colors = o3d.utility.Vector3dVector(colors.astype(np.float64) / 255.0)
        o3d.io.write_point_cloud(output_ply, pcd)
        print(f"Point cloud saved: {output_ply} ({len(pts3d)} points)")

        return pts3d, xs_final, ys_final

    # Save all results
    def save_results(self, output_dir, depth_image=None, pts3d=None, xs=None, ys=None):
        os.makedirs(output_dir, exist_ok=True)
        cv2.imwrite(os.path.join(output_dir, "mask.png"), (self.mask * 255).astype(np.uint8))

        if np.any(self.x_map):
            x_map_vis = cv2.normalize(self.x_map.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX)
            cv2.imwrite(os.path.join(output_dir, "x_map.png"), x_map_vis.astype(np.uint8))

        if np.any(self.y_map):
            y_map_vis = cv2.normalize(self.y_map.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX)
            cv2.imwrite(os.path.join(output_dir, "y_map.png"), y_map_vis.astype(np.uint8))

        if depth_image is not None:
            valid = depth_image > 0
            if np.any(valid):
                dmin, dmax = depth_image[valid].min(), depth_image[valid].max()
                depth_vis = np.zeros_like(depth_image, dtype=np.uint8)
                depth_vis[valid] = ((depth_image[valid] - dmin) / (dmax - dmin + 1e-8) * 255).astype(np.uint8)
                cv2.imwrite(os.path.join(output_dir, "depth_vis.png"), depth_vis)
            np.save(os.path.join(output_dir, "depth_raw.npy"), depth_image)
                    
        if pts3d is not None and xs is not None and ys is not None:
            ply_path = os.path.join(output_dir, "pointcloud.ply")
            try:
                ref_img = self._load_captured_image("reference_white.png")
                vals = ref_img[ys, xs]
                colors = np.stack([vals, vals, vals], axis=1).astype(np.uint8)
            except Exception:
                colors = None

            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(pts3d)
            if colors is not None:
                pcd.colors = o3d.utility.Vector3dVector(colors.astype(np.float64) / 255.0)
            o3d.io.write_point_cloud(ply_path, pcd)
            print(f"Point cloud file saved: {ply_path}")
            
    def compute_depth_map_from_pointcloud(self, pts3d, xs, ys):
        depth = np.zeros((self.height, self.width), dtype=np.float32)
        zvals = pts3d[:, 2]

        # Filter out out-of-bounds indices
        valid = (xs >= 0) & (xs < self.width) & (ys >= 0) & (ys < self.height)
        xs, ys, zvals = xs[valid], ys[valid], zvals[valid]

        depth[ys, xs] = zvals
        return depth


if __name__ == "__main__":
    # === Only need to modify here ===
    CAPTURED_DIR = "D:\\zju\\dasanshang\\Intelligent_version\\scan\\graycode\\noon\\2"
    OUTPUT_DIR = "D:\\zju\\dasanshang\\Intelligent_version\\scan\\noon\\reconstruction_result_2_2"

    Kc = np.array([[3.6838333907732294e+003, 0., 1.2500944196559094e+003],
                   [0., 3.6974474889257835e+003, 1.0122781917607587e+003],
                   [0., 0., 1.]], dtype=np.float64)
    dist_c = np.array([-5.1558942293476151e-001, 7.9382621058611061e-002,
                       1.9059474312756614e-004, 3.5905157827651230e-003, 0.])

    Kp = np.array([[2.8013622132143819e+003, 0., 5.3714564964254430e+002],
                   [0., 2.7957271561105604e+003, 8.1512682665321393e+002],
                   [0., 0., 1.]], dtype=np.float64)
    dist_p = np.array([3.3709414619914682e-002, 3.9240756191495979e-001,
                       1.5743724471346715e-004, 6.1563512624725311e-004, 0.])

    R = np.array([[9.8097166816623960e-001, 1.9129352460664582e-002, -1.9320624764634459e-001],
                  [3.8199208382748290e-003, 9.9303996753376567e-001, 1.1771589138823595e-001],
                  [1.9411335466663360e-001, -1.1621398691626285e-001, 9.7407100089525933e-001]])
    T = np.array([[1.7194845987298550e+001],
                  [-1.2098438607071827e+001],
                  [-6.8266691762771616e+000]])

    recon = GrayCodeReconstructor(
        graycode_dir=None,        # Directory for generating patterns is not needed
        captured_dir=CAPTURED_DIR,
        width=1920,
        height=1080,
        nbits=11,
        cam_dist=dist_c,
        proj_dist=dist_p
    )

    # 🔹 Only decode and reconstruct, do not generate any patterns
    recon.decode_graycode()
    pts3d, xs, ys = recon.compute_point_cloud(Kc, Kp, R, T,
                                              output_ply=os.path.join(OUTPUT_DIR, "output.ply"))
    depth_img = recon.compute_depth_map_from_pointcloud(pts3d, xs, ys)
    recon.save_results(OUTPUT_DIR, depth_image=depth_img, pts3d=pts3d, xs=xs, ys=ys)
    print("Reconstruction process completed. Output directory:", OUTPUT_DIR)