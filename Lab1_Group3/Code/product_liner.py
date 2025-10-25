import os
import re
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from sklearn.linear_model import LinearRegression

def collect_image_data(folder_path,saturation_threshold=210):

    data = {
        'exposure': [],
        'gain': [],
        'brightness': [],
        'r_mean': [],
        'g_mean': [],
        'b_mean': [],
        'gain_exposure_product': [] 
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
                product = gain_value * exp_value 
                
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
                        data['gain_exposure_product'].append(product)
                        data['r_mean'].append(r_mean)
                        data['g_mean'].append(g_mean)
                        data['b_mean'].append(b_mean)
                except Exception as e:
                    print(f"{filename}error: {e}")

    for key in data:
        data[key] = np.array(data[key])
    
    return data

# RGB = k*(gain×exposure) + b
def fit_product_model(X, y):
    X_reshaped = X.reshape(-1, 1)
    model = LinearRegression()
    model.fit(X_reshaped, y)
    k = model.coef_[0] 
    b = model.intercept_ 
    r2 = model.score(X_reshaped, y) 
    return k, b, r2

def plot_results(groups_data):
    channels = [
        ('r_mean', 'R', 'red'),
        ('g_mean', 'G', 'green'),
        ('b_mean', 'B', 'blue')
    ]
    all_models = {}
    
    # 为每个组创建图像
    for group_name, data in groups_data.items():
        all_models[group_name] = {}
        X = data['gain_exposure_product']  
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle(f'{group_name} relationship between RGB and gain x exposure', fontsize=16)
        
        for i, (channel, label, color) in enumerate(channels):
            ax = axes[i]
            ax.scatter(X, data[channel], c=color, alpha=0.6, label='data')
            k, b, r2 = fit_product_model(X, data[channel])
            all_models[group_name][channel] = (k, b, r2)
            
            x_range = np.linspace(X.min(), X.max(), 100)
            y_pred = k * x_range + b
            ax.plot(x_range, y_pred, 'k--', linewidth=2, label='fitting line')
            
            channel_symbol = label.split()[0]
            equation = f'{channel_symbol} = {k:.6f}×(gain×exposure) + {b:.2f}'
            ax.text(0.05, 0.95, equation, transform=ax.transAxes,
                    bbox=dict(facecolor='white', alpha=0.8), fontsize=10)
            ax.text(0.05, 0.85, f'R² = {r2:.4f}', transform=ax.transAxes,
                    bbox=dict(facecolor='white', alpha=0.8), fontsize=10)
            
            ax.set_xlabel('gain × exposure', fontsize=10)
            ax.set_ylabel(f'{label}average', fontsize=10)
            ax.legend()
        
        plt.tight_layout(rect=[0, 0, 1, 0.96]) 
        save_path = f'rgb_vs_gainXexposure_{group_name}.png'
        plt.savefig(save_path, dpi=300)
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
            continue
        
        data = collect_image_data(folder_path)
        
        if len(data['exposure']) == 0:
            continue
            
        groups_data[group_name] = data
    
    if not groups_data:
        return
    
    models = plot_results(groups_data)
    
    print("\nfitting result")
    for group_name, channels in models.items():
        print(f"\n【{group_name}】")
        for channel, (k, b, r2) in channels.items():
            channel_name = {
                'r_mean': 'R',
                'g_mean': 'G',
                'b_mean': 'B'
            }[channel]
            print(f"{channel_name}: {channel_name.split()[0]} = {k:.6f}×(gain×exposure) + {b:.2f}")
            print(f" R² = {r2:.4f}")

if __name__ == "__main__":
    main()
    