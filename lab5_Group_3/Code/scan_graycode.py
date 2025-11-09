import numpy as np
import cv2
import os  # For directory operations

def binary_to_gray(binary: int) -> int:
    """Core function to convert binary to Gray code"""
    return binary ^ (binary >> 1)

class GrayCodeGenerator:
    def __init__(self, width: int, height: int, nbit: int):
        self.width = width        # Image width (1920)
        self.height = height      # Image height (1080)
        self.nbit = nbit          # Number of Gray code bits (11)
        self.vbits = nbit         # Number of bits used for vertical direction
        self.hbits = nbit         # Number of bits used for horizontal direction
        self.voffset = ((1 << self.vbits) - self.width) // 2   # Vertical offset (for center alignment)
        self.hoffset = ((1 << self.hbits) - self.height) // 2  # Horizontal offset (for center alignment)

    def generate_vertical_pattern(self, bit: int, inverted: bool) -> np.ndarray:
        """Generate vertical Gray code pattern (column index participates in calculation)"""
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        vmask = 1 << bit  # Current bit mask
        for h in range(self.height):
            for w in range(self.width):
                # Calculate Gray code and extract current bit
                gray_val = binary_to_gray(w + self.voffset) & vmask
                # Set pixel value based on inversion (255 for white, 0 for black)
                pixel = 255 if (gray_val != 0) else 0
                if inverted:
                    pixel = 255 - pixel
                pattern[h, w] = pixel
        return pattern

    def generate_horizontal_pattern(self, bit: int, inverted: bool) -> np.ndarray:
        """Generate horizontal Gray code pattern (row index participates in calculation)"""
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        hmask = 1 << bit  # Current bit mask
        for h in range(self.height):
            for w in range(self.width):
                # Calculate Gray code and extract current bit
                gray_val = binary_to_gray(h + self.hoffset) & hmask
                # Set pixel value based on inversion
                pixel = 255 if (gray_val != 0) else 0
                if inverted:
                    pixel = 255 - pixel
                pattern[h, w] = pixel
        return pattern

    def generate_reference_image(self, is_white: bool) -> np.ndarray:
        """Generate pure black/white reference image"""
        pixel_value = 255 if is_white else 0
        return np.full((self.height, self.width), pixel_value, dtype=np.uint8)

if __name__ == "__main__":
    # Create save directory if it doesn't exist
    save_dir = "new_graycode"
    os.makedirs(save_dir, exist_ok=True)  # exist_ok=True to avoid error when directory already exists
    
    # Initialize generator (1920×1080, 11-bit Gray code)
    generator = GrayCodeGenerator(width=1920, height=1080, nbit=11)
    
    # Pure black reference image
    black_img = generator.generate_reference_image(is_white=False)
    black_path = f"{save_dir}/reference_black.png"
    cv2.imwrite(black_path, black_img)
    print(f"Reference image saved: {black_path}")
    
    # Pure white reference image
    white_img = generator.generate_reference_image(is_white=True)
    white_path = f"{save_dir}/reference_white.png"
    cv2.imwrite(white_path, white_img)
    print(f"Reference image saved: {white_path}")
    
    # Generate vertical patterns (bit 0~10, each bit includes normal and inverted versions)
    for bit in range(generator.nbit):
        # Normal pattern
        normal_pat = generator.generate_vertical_pattern(bit, inverted=False)
        normal_path = f"{save_dir}/graycode_bit{bit:02d}_vertical_normal.png"
        cv2.imwrite(normal_path, normal_pat)
        
        # Inverted pattern
        inverted_pat = generator.generate_vertical_pattern(bit, inverted=True)
        inverted_path = f"{save_dir}/graycode_bit{bit:02d}_vertical_inverted.png"
        cv2.imwrite(inverted_path, inverted_pat)
        print(f"Vertical bit {bit} saved: {normal_path}, {inverted_path}")
    
    # Generate horizontal patterns (bit 0~10, each bit includes normal and inverted versions)
    for bit in range(generator.nbit):
        # Normal pattern
        normal_pat = generator.generate_horizontal_pattern(bit, inverted=False)
        normal_path = f"{save_dir}/graycode_bit{bit:02d}_horizontal_normal.png"
        cv2.imwrite(normal_path, normal_pat)
        
        # Inverted pattern
        inverted_pat = generator.generate_horizontal_pattern(bit, inverted=True)
        inverted_path = f"{save_dir}/graycode_bit{bit:02d}_horizontal_inverted.png"
        cv2.imwrite(inverted_path, inverted_pat)
        print(f"Horizontal bit {bit} saved: {normal_path}, {inverted_path}")

print(f"\nAll images have been saved to: {os.path.abspath(save_dir)}")