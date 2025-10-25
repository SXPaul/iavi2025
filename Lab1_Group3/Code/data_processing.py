import os
import re
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
from scipy.optimize import curve_fit
from collections import defaultdict

def parse_filename(filename):
    # 解析文件名以提取a、曝光时间、增益和亮度参数
    pattern = r"img_(\d+)_exp(\d+)_gain(\d+)_bright(\d+)\.png"
    match = re.match(pattern, filename)
    if match:
        a = int(match.group(1))
        exposure = int(match.group(2))
        gain = int(match.group(3))
        brightness = int(match.group(4))
        return a, exposure, gain, brightness
    return None

def get_average_rgb(image_path):
    # 计算图像的平均RGB值
    try:
        with Image.open(image_path) as img:
            img_rgb = img.convert('RGB')  # 转换为RGB模式
            img_array = np.array(img_rgb)  # 转换为numpy数组
            # 计算每个通道的平均值
            avg_r = np.mean(img_array[:, :, 0])
            avg_g = np.mean(img_array[:, :, 1])
            avg_b = np.mean(img_array[:, :, 2])
            return avg_r, avg_g, avg_b
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def collect_image_data(directory):
    # 从指定目录中所有格式正确的图像中收集数据
    data = []
    # 遍历目录中的所有文件
    for filename in os.listdir(directory):
        if filename.endswith('.png'):
            # 解析文件名
            params = parse_filename(filename)
            if params:
                a, exposure, gain, brightness = params
                # 获取完整图像路径
                image_path = os.path.join(directory, filename)
                # 获取平均RGB值
                rgb = get_average_rgb(image_path)
                if rgb:
                    r, g, b = rgb
                    data.append({
                        'a': a,
                        'exposure': exposure,
                        'gain': gain,
                        'brightness': brightness,
                        'r': r,
                        'g': g,
                        'b': b
                    })
                    print(f"Processed: {filename}")
    return data

# 两段线性拟合函数（通用，可支持曝光时间/增益作为自变量）
def two_segment_linear(x, m1, b1, m2, b2, x0):
    """
    两段线性函数：
    - 第一段（未饱和区域）：y = m1*x + b1（当x < x0时，x0为饱和点）
    - 第二段（饱和区域）：y = m2*x + b2（当x >= x0时）
    """
    return np.where(x < x0, m1 * x + b1, m2 * x + b2)

def find_saturation_point(x_data, y_data):
    # 检测饱和点：当斜率降至最大值的30%时判定为饱和开始
    if len(x_data) < 4:  # 数据点数量不足，无法可靠检测
        return None
    
    # 按自变量（x_data）对数据排序
    sorted_indices = np.argsort(x_data)
    x_sorted = np.array(x_data)[sorted_indices]
    y_sorted = np.array(y_data)[sorted_indices]
    
    # 计算相邻数据点间的斜率
    slopes = np.diff(y_sorted) / np.diff(x_sorted)
    max_slope = np.max(slopes)
    threshold = 0.3 * max_slope  # 斜率低于最大值30%时视为进入饱和
    
    # 找到第一个低于阈值的斜率对应的x值（即饱和点）
    for i, slope in enumerate(slopes):
        if slope < threshold:
            return x_sorted[i+1]  # 返回饱和开始时的自变量值
    return None  # 未检测到明显饱和点

def group_data_by_exposure(data):
    """按曝光时间对每个颜色通道的数据进行分组（用于分析增益与RGB值的关系）"""
    r_data = defaultdict(lambda: {'gains': [], 'values': []})
    g_data = defaultdict(lambda: {'gains': [], 'values': []})
    b_data = defaultdict(lambda: {'gains': [], 'values': []})
    
    for entry in data:
        exp = entry['exposure']
        # 按曝光时间分组，存储对应的增益和RGB值
        r_data[exp]['gains'].append(entry['gain'])
        r_data[exp]['values'].append(entry['r'])
        
        g_data[exp]['gains'].append(entry['gain'])
        g_data[exp]['values'].append(entry['g'])
        
        b_data[exp]['gains'].append(entry['gain'])
        b_data[exp]['values'].append(entry['b'])
    
    return r_data, g_data, b_data

def group_data_by_gain(data):
    """按增益对每个颜色通道的数据进行分组（用于分析曝光时间与RGB值的关系）"""
    r_data = defaultdict(lambda: {'exposures': [], 'values': []})
    g_data = defaultdict(lambda: {'exposures': [], 'values': []})
    b_data = defaultdict(lambda: {'exposures': [], 'values': []})
    
    for entry in data:
        gain = entry['gain']
        r_data[gain]['exposures'].append(entry['exposure'])
        r_data[gain]['values'].append(entry['r'])
        
        g_data[gain]['exposures'].append(entry['exposure'])
        g_data[gain]['values'].append(entry['g'])
        
        b_data[gain]['exposures'].append(entry['exposure'])
        b_data[gain]['values'].append(entry['b'])
    
    return r_data, g_data, b_data

def plot_3d_figures(data):
    # 原有3D图绘制功能
    if not data:
        print("No data available for plotting")
        return
    
    exposures = [d['exposure'] for d in data]
    gains = [d['gain'] for d in data]
    r_values = [d['r'] for d in data]
    g_values = [d['g'] for d in data]
    b_values = [d['b'] for d in data]
    
    all_gains = sorted(set(gains))
    colors = cm.rainbow(np.linspace(0, 1, len(all_gains)))
    gain_color_map = {gain: color for gain, color in zip(all_gains, colors)}
    
    fig = plt.figure(figsize=(18, 6))
    
    # 绘制R通道3D图
    ax1 = fig.add_subplot(131, projection='3d')
    for gain in all_gains:
        mask = [g == gain for g in gains]
        ax1.scatter(np.array(exposures)[mask], np.array(gains)[mask], np.array(r_values)[mask], 
                   c=[gain_color_map[gain]], marker='o', label=f'Gain = {gain}')
    ax1.set_xlabel('Exposure Time')
    ax1.set_ylabel('Gain')
    ax1.set_zlabel('Red Channel Value')
    ax1.set_title('Red Value vs Exposure & Gain')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 绘制G通道3D图
    ax2 = fig.add_subplot(132, projection='3d')
    for gain in all_gains:
        mask = [g == gain for g in gains]
        ax2.scatter(np.array(exposures)[mask], np.array(gains)[mask], np.array(g_values)[mask], 
                   c=[gain_color_map[gain]], marker='o', label=f'Gain = {gain}')
    ax2.set_xlabel('Exposure Time')
    ax2.set_ylabel('Gain')
    ax2.set_zlabel('Green Channel Value')
    ax2.set_title('Green Value vs Exposure & Gain')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 绘制B通道3D图
    ax3 = fig.add_subplot(133, projection='3d')
    for gain in all_gains:
        mask = [g == gain for g in gains]
        ax3.scatter(np.array(exposures)[mask], np.array(gains)[mask], np.array(b_values)[mask], 
                   c=[gain_color_map[gain]], marker='o', label=f'Gain = {gain}')
    ax3.set_xlabel('Exposure Time')
    ax3.set_ylabel('Gain')
    ax3.set_zlabel('Blue Channel Value')
    ax3.set_title('Blue Value vs Exposure & Gain')
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    return fig

def plot_2d_figures(data):
    if not data:
        print("No data available for plotting")
        return
    

    # 按增益分组：分析曝光时间与RGB值的关系
    r_by_gain, g_by_gain, b_by_gain = group_data_by_gain(data)
    # 按曝光时间分组：分析增益与RGB值的关系
    r_by_exp, g_by_exp, b_by_exp = group_data_by_exposure(data)
    
    # 颜色映射配置
    all_gains = sorted(set(r_by_gain.keys()).union(g_by_gain.keys()).union(b_by_gain.keys()))
    all_exps = sorted(set(r_by_exp.keys()).union(g_by_exp.keys()).union(b_by_exp.keys()))
    gain_colors = cm.rainbow(np.linspace(0, 1, len(all_gains)))  # 增益用彩虹色映射
    exp_colors = cm.plasma(np.linspace(0, 1, len(all_exps)))    # 曝光时间用等离子色映射（与增益区分）
    gain_color_map = {g: c for g, c in zip(all_gains, gain_colors)}
    exp_color_map = {e: c for e, c in zip(all_exps, exp_colors)}
    
    # 创建2D图
    fig = plt.figure(figsize=(20, 12))
    
    # 存储所有拟合方程（
    equations = {
        # 固定增益，曝光时间为变量
        'fixed_gain_exposure_var': {'red': {}, 'green': {}, 'blue': {}},
        # 固定曝光时间，增益为变量
        'fixed_exp_gain_var': {'red': {}, 'green': {}, 'blue': {}}
    }

    # R通道：固定增益 → 曝光时间变量
    ax1 = fig.add_subplot(231)
    for gain, gain_data in sorted(r_by_gain.items()):
        # 对数据排序
        sorted_idx = np.argsort(gain_data['exposures'])
        exps = np.array(gain_data['exposures'])[sorted_idx]
        vals = np.array(gain_data['values'])[sorted_idx]
        
        # 绘制数据点
        ax1.scatter(exps, vals, c=gain_color_map[gain], alpha=0.7, label=f'Gain={gain}')
        
        # 两段拟合
        if len(exps) >= 4:
            try:
                x0_guess = find_saturation_point(exps, vals) or np.median(exps)
                p0 = [0.001, 10, 0.0001, 240, x0_guess]  # 适配曝光时间范围（500-25000）
                popt, _ = curve_fit(two_segment_linear, exps, vals, p0=p0, maxfev=10000)
                m1, b1, m2, b2, x0 = popt
                
                # 绘制拟合线
                x_fit = np.linspace(min(exps), max(exps), 200)
                y_fit = two_segment_linear(x_fit, *popt)
                ax1.plot(x_fit, y_fit, '--', c=gain_color_map[gain])
                
                # 标记饱和点
                ax1.axvline(x=x0, c=gain_color_map[gain], linestyle=':', alpha=0.5)
                ax1.plot(x0, two_segment_linear(x0, *popt), 'ko', markersize=5, label='Saturation' if gain==all_gains[0] else "")
                
                # 存储方程（斜率保留4位小数）
                eq = f'Gain={gain}:\n  Unsaturated: y={m1:.4f}x+{b1:.2f}\n  Saturated: y={m2:.4f}x+{b2:.2f}\n  Saturation Exp: {x0:.0f}'
                equations['fixed_gain_exposure_var']['red'][gain] = eq
            except:
                # 备用方案：简单线性拟合
                if len(exps) >= 2:
                    m, b = np.polyfit(exps, vals, 1)
                    x_fit = np.linspace(min(exps), max(exps), 100)
                    ax1.plot(x_fit, m*x_fit + b, '--', c=gain_color_map[gain], alpha=0.5)
                    equations['fixed_gain_exposure_var']['red'][gain] = f'Gain={gain}:\n  Linear Fit: y={m:.4f}x+{b:.2f}'
    ax1.set_xlabel('Exposure Time')
    ax1.set_ylabel('Red Channel Value')
    ax1.set_title('Fixed Gain → Red Value vs Exposure')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.grid(True, alpha=0.3)

    # G通道：固定增益 → 曝光时间变量（同上述逻辑）
    ax2 = fig.add_subplot(232)
    for gain, gain_data in sorted(g_by_gain.items()):
        sorted_idx = np.argsort(gain_data['exposures'])
        exps = np.array(gain_data['exposures'])[sorted_idx]
        vals = np.array(gain_data['values'])[sorted_idx]
        
        ax2.scatter(exps, vals, c=gain_color_map[gain], alpha=0.7, label=f'Gain={gain}')
        if len(exps) >= 4:
            try:
                x0_guess = find_saturation_point(exps, vals) or np.median(exps)
                p0 = [0.001, 10, 0.0001, 240, x0_guess]
                popt, _ = curve_fit(two_segment_linear, exps, vals, p0=p0, maxfev=10000)
                m1, b1, m2, b2, x0 = popt
                
                x_fit = np.linspace(min(exps), max(exps), 200)
                y_fit = two_segment_linear(x_fit, *popt)
                ax2.plot(x_fit, y_fit, '--', c=gain_color_map[gain])
                
                ax2.axvline(x=x0, c=gain_color_map[gain], linestyle=':', alpha=0.5)
                ax2.plot(x0, two_segment_linear(x0, *popt), 'ko', markersize=5)
                
                eq = f'Gain={gain}:\n  Unsaturated: y={m1:.4f}x+{b1:.2f}\n  Saturated: y={m2:.4f}x+{b2:.2f}\n  Saturation Exp: {x0:.0f}'
                equations['fixed_gain_exposure_var']['green'][gain] = eq
            except:
                if len(exps) >= 2:
                    m, b = np.polyfit(exps, vals, 1)
                    x_fit = np.linspace(min(exps), max(exps), 100)
                    ax2.plot(x_fit, m*x_fit + b, '--', c=gain_color_map[gain], alpha=0.5)
                    equations['fixed_gain_exposure_var']['green'][gain] = f'Gain={gain}:\n  Linear Fit: y={m:.4f}x+{b:.2f}'
    ax2.set_xlabel('Exposure Time')
    ax2.set_ylabel('Green Channel Value')
    ax2.set_title('Fixed Gain → Green Value vs Exposure')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax2.grid(True, alpha=0.3)

    # B通道：固定增益 → 曝光时间变量（同上述逻辑）
    ax3 = fig.add_subplot(233)
    for gain, gain_data in sorted(b_by_gain.items()):
        sorted_idx = np.argsort(gain_data['exposures'])
        exps = np.array(gain_data['exposures'])[sorted_idx]
        vals = np.array(gain_data['values'])[sorted_idx]
        
        ax3.scatter(exps, vals, c=gain_color_map[gain], alpha=0.7, label=f'Gain={gain}')
        if len(exps) >= 4:
            try:
                x0_guess = find_saturation_point(exps, vals) or np.median(exps)
                p0 = [0.001, 10, 0.0001, 240, x0_guess]
                popt, _ = curve_fit(two_segment_linear, exps, vals, p0=p0, maxfev=10000)
                m1, b1, m2, b2, x0 = popt
                
                x_fit = np.linspace(min(exps), max(exps), 200)
                y_fit = two_segment_linear(x_fit, *popt)
                ax3.plot(x_fit, y_fit, '--', c=gain_color_map[gain])
                
                ax3.axvline(x=x0, c=gain_color_map[gain], linestyle=':', alpha=0.5)
                ax3.plot(x0, two_segment_linear(x0, *popt), 'ko', markersize=5)
                
                eq = f'Gain={gain}:\n  Unsaturated: y={m1:.4f}x+{b1:.2f}\n  Saturated: y={m2:.4f}x+{b2:.2f}\n  Saturation Exp: {x0:.0f}'
                equations['fixed_gain_exposure_var']['blue'][gain] = eq
            except:
                if len(exps) >= 2:
                    m, b = np.polyfit(exps, vals, 1)
                    x_fit = np.linspace(min(exps), max(exps), 100)
                    ax3.plot(x_fit, m*x_fit + b, '--', c=gain_color_map[gain], alpha=0.5)
                    equations['fixed_gain_exposure_var']['blue'][gain] = f'Gain={gain}:\n  Linear Fit: y={m:.4f}x+{b:.2f}'
    ax3.set_xlabel('Exposure Time')
    ax3.set_ylabel('Blue Channel Value')
    ax3.set_title('Fixed Gain → Blue Value vs Exposure')
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax3.grid(True, alpha=0.3)

    # R通道：固定曝光时间 → 增益变量
    ax4 = fig.add_subplot(234)
    for exp, exp_data in sorted(r_by_exp.items()):
        # 对数据排序（按增益升序）
        sorted_idx = np.argsort(exp_data['gains'])
        gains = np.array(exp_data['gains'])[sorted_idx]
        vals = np.array(exp_data['values'])[sorted_idx]
        
        # 绘制数据点
        ax4.scatter(gains, vals, c=exp_color_map[exp], alpha=0.7, label=f'Exposure={exp}')
        
        # 两段拟合
        if len(gains) >= 4:
            try:
                x0_guess = find_saturation_point(gains, vals) or np.median(gains)
                p0 = [1, 5, 0.1, 240, x0_guess]  # 适配增益范围（2-25）
                popt, _ = curve_fit(two_segment_linear, gains, vals, p0=p0, maxfev=10000)
                m1, b1, m2, b2, x0 = popt
                
                # 绘制拟合线
                x_fit = np.linspace(min(gains), max(gains), 200)
                y_fit = two_segment_linear(x_fit, *popt)
                ax4.plot(x_fit, y_fit, '--', c=exp_color_map[exp])
                
                # 标记饱和点
                ax4.axvline(x=x0, c=exp_color_map[exp], linestyle=':', alpha=0.5)
                ax4.plot(x0, two_segment_linear(x0, *popt), 's', color='black', markersize=5, label='Saturation' if exp==all_exps[0] else "")
                
                # 存储方程
                eq = f'Exposure={exp}:\n  Unsaturated: y={m1:.4f}x+{b1:.2f}\n  Saturated: y={m2:.4f}x+{b2:.2f}\n  Saturation Gain: {x0:.1f}'
                equations['fixed_exp_gain_var']['red'][exp] = eq
            except:
                # 备用方案：简单线性拟合
                if len(gains) >= 2:
                    m, b = np.polyfit(gains, vals, 1)
                    x_fit = np.linspace(min(gains), max(gains), 100)
                    ax4.plot(x_fit, m*x_fit + b, '--', c=exp_color_map[exp], alpha=0.5)
                    equations['fixed_exp_gain_var']['red'][exp] = f'Exposure={exp}:\n  Linear Fit: y={m:.4f}x+{b:.2f}'
    ax4.set_xlabel('Gain')
    ax4.set_ylabel('Red Channel Value')
    ax4.set_title('Fixed Exposure → Red Value vs Gain')
    ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax4.grid(True, alpha=0.3)

    # G通道：固定曝光时间 → 增益变量
    ax5 = fig.add_subplot(235)
    for exp, exp_data in sorted(g_by_exp.items()):
        sorted_idx = np.argsort(exp_data['gains'])
        gains = np.array(exp_data['gains'])[sorted_idx]
        vals = np.array(exp_data['values'])[sorted_idx]
        
        ax5.scatter(gains, vals, c=exp_color_map[exp], alpha=0.7, label=f'Exposure={exp}')
        if len(gains) >= 4:
            try:
                x0_guess = find_saturation_point(gains, vals) or np.median(gains)
                p0 = [1, 5, 0.1, 240, x0_guess]
                popt, _ = curve_fit(two_segment_linear, gains, vals, p0=p0, maxfev=10000)
                m1, b1, m2, b2, x0 = popt
                
                x_fit = np.linspace(min(gains), max(gains), 200)
                y_fit = two_segment_linear(x_fit, *popt)
                ax5.plot(x_fit, y_fit, '--', c=exp_color_map[exp])
                
                ax5.axvline(x=x0, c=exp_color_map[exp], linestyle=':', alpha=0.5)
                ax5.plot(x0, two_segment_linear(x0, *popt), 's', color='black', markersize=5)
                
                eq = f'Exposure={exp}:\n  Unsaturated: y={m1:.4f}x+{b1:.2f}\n  Saturated: y={m2:.4f}x+{b2:.2f}\n  Saturation Gain: {x0:.1f}'
                equations['fixed_exp_gain_var']['green'][exp] = eq
            except:
                if len(gains) >= 2:
                    m, b = np.polyfit(gains, vals, 1)
                    x_fit = np.linspace(min(gains), max(gains), 100)
                    ax5.plot(x_fit, m*x_fit + b, '--', c=exp_color_map[exp], alpha=0.5)
                    equations['fixed_exp_gain_var']['green'][exp] = f'Exposure={exp}:\n  Linear Fit: y={m:.4f}x+{b:.2f}'
    ax5.set_xlabel('Gain')
    ax5.set_ylabel('Green Channel Value')
    ax5.set_title('Fixed Exposure → Green Value vs Gain')
    ax5.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax5.grid(True, alpha=0.3)

    # B通道：固定曝光时间 → 增益变量
    ax6 = fig.add_subplot(236)
    for exp, exp_data in sorted(b_by_exp.items()):
        sorted_idx = np.argsort(exp_data['gains'])
        gains = np.array(exp_data['gains'])[sorted_idx]
        vals = np.array(exp_data['values'])[sorted_idx]
        
        ax6.scatter(gains, vals, c=exp_color_map[exp], alpha=0.7, label=f'Exposure={exp}')
        if len(gains) >= 4:
            try:
                x0_guess = find_saturation_point(gains, vals) or np.median(gains)
                p0 = [1, 5, 0.1, 240, x0_guess]
                popt, _ = curve_fit(two_segment_linear, gains, vals, p0=p0, maxfev=10000)
                m1, b1, m2, b2, x0 = popt
                
                x_fit = np.linspace(min(gains), max(gains), 200)
                y_fit = two_segment_linear(x_fit, *popt)
                ax6.plot(x_fit, y_fit, '--', c=exp_color_map[exp])
                
                ax6.axvline(x=x0, c=exp_color_map[exp], linestyle=':', alpha=0.5)
                ax6.plot(x0, two_segment_linear(x0, *popt), 's', color='black', markersize=5)
                
                eq = f'Exposure={exp}:\n  Unsaturated: y={m1:.4f}x+{b1:.2f}\n  Saturated: y={m2:.4f}x+{b2:.2f}\n  Saturation Gain: {x0:.1f}'
                equations['fixed_exp_gain_var']['blue'][exp] = eq
            except:
                if len(gains) >= 2:
                    m, b = np.polyfit(gains, vals, 1)
                    x_fit = np.linspace(min(gains), max(gains), 100)
                    ax6.plot(x_fit, m*x_fit + b, '--', c=exp_color_map[exp], alpha=0.5)
                    equations['fixed_exp_gain_var']['blue'][exp] = f'Exposure={exp}:\n  Linear Fit: y={m:.4f}x+{b:.2f}'
    ax6.set_xlabel('Gain')
    ax6.set_ylabel('Blue Channel Value')
    ax6.set_title('Fixed Exposure → Blue Value vs Gain')
    ax6.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()

    fig_eq = plt.figure(figsize=(20, 12))
    plt.title('RGB Channel Fitting Equations Summary (Two Variable Dimensions)', fontsize=16)
    plt.axis('off')  # 隐藏坐标轴

    # 1. 固定增益，曝光时间为变量（RGB通道）
    red_exp_text = "1. Fixed Gain, Exposure as Variable\n\n[Red Channel]\n"
    for gain in sorted(equations['fixed_gain_exposure_var']['red'].keys()):
        red_exp_text += equations['fixed_gain_exposure_var']['red'][gain] + "\n\n"
    plt.text(0.02, 0.98, red_exp_text, fontsize=9, verticalalignment='top',
             bbox=dict(facecolor='#FFEEEE', alpha=0.8, boxstyle='round,pad=0.5'))

    green_exp_text = "[Green Channel]\n"
    for gain in sorted(equations['fixed_gain_exposure_var']['green'].keys()):
        green_exp_text += equations['fixed_gain_exposure_var']['green'][gain] + "\n\n"
        plt.text(0.18, 0.98, green_exp_text, fontsize=9, verticalalignment='top',
             bbox=dict(facecolor='#FFEEEE', alpha=0.8, boxstyle='round,pad=0.5'))
    
    blue_exp_text = "[Blue Channel]\n"
    for gain in sorted(equations['fixed_gain_exposure_var']['blue'].keys()):
        blue_exp_text += equations['fixed_gain_exposure_var']['blue'][gain] + "\n\n"
    plt.text(0.34, 0.98, blue_exp_text, fontsize=9, verticalalignment='top',
             bbox=dict(facecolor='#FFEEEE', alpha=0.8, boxstyle='round,pad=0.5'))

    # 2. 固定曝光时间，增益为变量（RGB通道）
    red_gain_text = "2. Fixed Exposure, Gain as Variable\n\n[Red Channel]\n"
    for exp in sorted(equations['fixed_exp_gain_var']['red'].keys()):
        red_gain_text += equations['fixed_exp_gain_var']['red'][exp] + "\n\n"
    plt.text(0.52, 0.98, red_gain_text, fontsize=9, verticalalignment='top',
             bbox=dict(facecolor='#EEFFEE', alpha=0.8, boxstyle='round,pad=0.5'))

    green_gain_text = "[Green Channel]\n"
    for exp in sorted(equations['fixed_exp_gain_var']['green'].keys()):
        green_gain_text += equations['fixed_exp_gain_var']['green'][exp] + "\n\n"
    plt.text(0.68, 0.98, green_gain_text, fontsize=9, verticalalignment='top',
             bbox=dict(facecolor='#EEFFEE', alpha=0.8, boxstyle='round,pad=0.5'))
    
    blue_gain_text = "[Blue Channel]\n"
    for exp in sorted(equations['fixed_exp_gain_var']['blue'].keys()):
        blue_gain_text += equations['fixed_exp_gain_var']['blue'][exp] + "\n\n"
    plt.text(0.84, 0.98, blue_gain_text, fontsize=9, verticalalignment='top',
             bbox=dict(facecolor='#EEFFEE', alpha=0.8, boxstyle='round,pad=0.5'))

    plt.tight_layout()
    return fig, fig_eq

def plot_rgb_vs_exposure_and_gain(data):
    # 主绘图函数
    if not data:
        print("No data available for plotting")
        return
    
    # 保存3D图
    fig3d = plot_3d_figures(data)
    fig3d.savefig('rgb_3d_analysis.png', dpi=300, bbox_inches='tight')
    
    # 保存2D图和方程汇总图
    fig2d, fig_eq = plot_2d_figures(data)
    fig2d.savefig('rgb_2d_dual_analysis.png', dpi=300, bbox_inches='tight')
    fig_eq.savefig('rgb_fitting_equations_dual.png', dpi=300, bbox_inches='tight')
    
    print("Analysis results saved as:")
    print("- 'rgb_3d_analysis.png' (3D Relationship Plot)")
    print("- 'rgb_2d_dual_analysis.png' (2D Dual-Variable Analysis Plot)")
    print("- 'rgb_fitting_equations_dual.png' (Fitting Equations Summary)")
    plt.show()

def main():

    directory = "D:\\zju\\dasanshang\\Intelligent_version\\lab\\1\\capture_2025-09-19_15-53\\capture_2025-09-19_15-53\\group1_iso_vary_exposure"
    
    # 检查目录有效性
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist")
        return
    
    # 收集并分析数据
    print("Collecting and analyzing image data...")
    image_data = collect_image_data(directory)
    
    if not image_data:
        print("No images with valid format found")
        return
    
    # 生成图表
    print("Generating analysis plots...")
    plot_rgb_vs_exposure_and_gain(image_data)
    
    print("Analysis completed!")

if __name__ == "__main__":
    main()