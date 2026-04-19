import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

class CalibrationCore:
    def __init__(self):
        pass

    def gaussian(self, x, a, x0, sigma, offset):
        return a * np.exp(-(x - x0)**2 / (2 * sigma**2)) + offset

    def find_and_fit_peaks(self, y_data, prominence_multiplier=3.5):
        """スペクトルからピークを検索し、それぞれをガウシアンでフィットする"""
        x_data = np.arange(len(y_data))
        
        # 背景ノイズレベルの推定
        # 全体の中央値より下にあるデータ（ベースライン）の標準偏差をノイズの大きさとみなす
        median_y = np.median(y_data)
        baseline_data = y_data[y_data <= median_y]
        noise = np.std(baseline_data) if len(baseline_data) > 0 else 1.0
        
        # カウント数が極端に低い（フラットな）場合の安全策
        if noise < 1.0: 
            noise = 1.0
        
        prominence_threshold = noise * prominence_multiplier
        height_threshold = median_y + noise * max(1.0, prominence_multiplier)
        print(f"Peak find, prominence_multiplier: {prominence_multiplier}, noise: {noise:.2f}, prominence_thresh: {prominence_threshold:.2f}, height_thresh: {height_threshold:.2f}")

        peaks, properties = find_peaks(y_data, prominence=prominence_threshold, height=height_threshold)

        fitted_peaks = []
        for p in peaks:
            # ピークの周囲数ピクセル（例: ±10ピクセル）を切り出してフィット
            window = 10
            start = max(0, p - window)
            end = min(len(y_data), p + window + 1)
            
            x_fit = x_data[start:end]
            y_fit = y_data[start:end]
            
            # 初期推定値: a=ピーク高さ, x0=ピーク位置, sigma=2.0, offset=最小値
            a_guess = y_data[p] - np.min(y_fit)
            offset_guess = np.min(y_fit)
            p0 = [a_guess, p, 2.0, offset_guess]
            bounds = ([0, min(x_fit), 0.1, -np.inf], [np.inf, max(x_fit), 20, np.inf])
            
            try:
                popt, _ = curve_fit(self.gaussian, x_fit, y_fit, p0=p0, bounds=bounds)
                y_curve = self.gaussian(x_fit, *popt)
                fitted_peaks.append({
                    "center": popt[1],
                    "x_fit": x_fit,
                    "y_data": y_fit,
                    "y_curve": y_curve
                })
            except:
                # フィット失敗時は元データをそのまま返す
                fitted_peaks.append({
                    "center": float(p),
                    "x_fit": x_fit,
                    "y_data": y_fit,
                    "y_curve": y_fit
                })
                
        return fitted_peaks

    def calibrate(self, pixels, ref_values):
        """ピクセルと基準値(nm または cm⁻¹)のリストを受け取り、多項式フィットを行う"""
        pixels = np.array(pixels)
        ref_values = np.array(ref_values)
        
        if len(pixels) < 2:
            return None
            
        if len(pixels) == 2:
            # 2点の場合は1次関数 (y = c1*x + c0)
            coeffs = np.polyfit(pixels, ref_values, 1)
            return {
                "c0": coeffs[1],
                "c1": coeffs[0],
                "c2": 0.0
            }
        else:
            # 3点以上の場合は2次関数 (y = c2*x^2 + c1*x + c0)
            coeffs = np.polyfit(pixels, ref_values, 2)
            return {
                "c0": coeffs[2],
                "c1": coeffs[1],
                "c2": coeffs[0]
            }