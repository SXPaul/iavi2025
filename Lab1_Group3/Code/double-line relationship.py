import os
import re
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image
from sklearn.linear_model import LinearRegression

def collect_image_data(folder_path,saturation_threshold=210):
    data = {
        'exposure': [],
        'gain': [],
        'brightness': [],
        'r_mean': [],
        'g_mean': [],
        'b_mean': []
    }
    
    pattern = r"img_\d+_exp(\d+)_gain(\d+)_bright(\d+)\.png"
    saturated_count = 0
    for filename in os.listdir(folder_path):
        if filename.endswith('.png'):
            match = re.match(pattern, filename)
            if match:
                exp_value = int(match.group(1))
                gain_value = int(match.group(2))
                bright_value = int(match.group(3))
                
                img_path = os.path.join(folder_path, filename)
                try:
                    with Image.open(img_path) as img:
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                            
                        img_array = np.array(img)
                        r_mean = np.mean(img_array[:, :, 0])
                        g_mean = np.mean(img_array[:, :, 1])
                        b_mean = np.mean(img_array[:, :, 2])
                        if r_mean > saturation_threshold or g_mean > saturation_threshold or b_mean > saturation_threshold:
                            saturated_count += 1
                            continue 
                        data['exposure'].append(exp_value)
                        data['gain'].append(gain_value)
                        data['brightness'].append(bright_value)
                        data['r_mean'].append(r_mean)
                        data['g_mean'].append(g_mean)
                        data['b_mean'].append(b_mean)
                except Exception as e:
                    print(f"{filename}error: {e}")

    for key in data:
        data[key] = np.array(data[key])
    
    return data

# RGB = k1*gain + k2*exposure + b
def fit_multivariate_model(X, y):
    model = LinearRegression()
    model.fit(X, y)
    k1, k2 = model.coef_ 
    b = model.intercept_
    r2 = model.score(X, y)
    return k1, k2, b, r2

def plot_results(groups_data):
    channels = [
        ('r_mean', 'R', 'red'),
        ('g_mean', 'G', 'green'),
        ('b_mean', 'B', 'blue')
    ]
    all_models = {}
    
    for group_name, data in groups_data.items():
        all_models[group_name] = {}
        X = np.column_stack((data['gain'], data['exposure']))

        fig = plt.figure(figsize=(18, 5))
        
        for i, (channel, label, color) in enumerate(channels, 1):
            ax = fig.add_subplot(1, 3, i, projection='3d')
            scatter = ax.scatter(data['gain'], data['exposure'], data[channel], 
                                c=color, alpha=0.6, label='data')
            k1, k2, b, r2 = fit_multivariate_model(X, data[channel])
            all_models[group_name][channel] = (k1, k2, b, r2)
            gain_range = np.linspace(data['gain'].min(), data['gain'].max(), 20)
            exp_range = np.linspace(data['exposure'].min(), data['exposure'].max(), 20)
            gain_grid, exp_grid = np.meshgrid(gain_range, exp_range)
            pred_grid = k1 * gain_grid + k2 * exp_grid + b
            surf = ax.plot_surface(gain_grid, exp_grid, pred_grid, color=color, 
                                 alpha=0.3, label='Fitting plane')
            
            ax.set_title(f'{group_name} - {label}')
            ax.set_xlabel('gain')
            ax.set_ylabel('exposure')
            ax.set_zlabel(f'{label}average')
            
            equation = f'{label.split()[0]} = {k1:.6f}*gain + {k2:.6f}*exposure + {b:.2f}'
            ax.text2D(0.05, 0.95, equation, transform=ax.transAxes, 
                     bbox=dict(facecolor='white', alpha=0.8))
            ax.text2D(0.05, 0.85, f'R² = {r2:.4f}', transform=ax.transAxes, 
                     bbox=dict(facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(f'rgb_vs_gain_exposure_{group_name}.png', dpi=300)
        plt.show()
    
    return all_models

def main():
    folders = {
        "group1_iso_vary_exposure": r"E:\code\NLP\iavi\lab1\capture_2025-09-19_15-53\group1_iso_vary_exposure",
        "group2_exposure_vary_iso": r"E:\code\NLP\iavi\lab1\capture_2025-09-19_15-53\group2_exposure_vary_iso"
    }
    
    groups_data = {}
    for group_name, folder_path in folders.items():
        if not os.path.exists(folder_path):
            print(f"folder {folder_path} doesn't exist")
            continue
            
        data = collect_image_data(folder_path)
            
        groups_data[group_name] = data
    
    if not groups_data:
        return
    
    models = plot_results(groups_data)
    
    # 打印拟合方程
    print("\nfitting result:")
    for group_name, channels in models.items():
        print(f"--- {group_name} ---")
        for channel, (k1, k2, b, r2) in channels.items():
            channel_name = {
                'r_mean': 'R',
                'g_mean': 'G',
                'b_mean': 'B'
            }[channel]
            print(f"{channel_name}: {channel_name.split()[0]} = {k1:.6f}*gain + {k2:.6f}*exposure + {b:.2f}")
            print(f"  R² = {r2:.4f}\n")

if __name__ == "__main__":
    main()
    