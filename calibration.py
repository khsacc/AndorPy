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
        
        # UIのスライダーから渡された倍率を使用（デフォルト: 3.5）
        prominence_threshold = noise * prominence_multiplier
        height_threshold = median_y + noise * max(1.0, prominence_multiplier)
        print(f"Peak find, prominence_multiplier: {prominence_multiplier}")
        
        # distance=10 に設定し、10px以内に密集した細かなノイズピークを排除する
        peaks, _ = find_peaks(y_data, distance=10, prominence=prominence_threshold, height=height_threshold)
        
        fitted_peaks = []
        for p in peaks:
            # ピーク周辺(±20px)を切り出してガウシアンフィット
            start = max(0, p - 20)
            end = min(len(y_data), p + 20)
            x_fit = x_data[start:end]
            y_fit = y_data[start:end]
            
            p_amp = y_data[p] - np.min(y_fit)
            offset_guess = np.min(y_fit)
            p0 = [p_amp, p, 2.0, offset_guess]
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

    def calibrate(self, pixels, wavelengths):
        """ピクセルと波長のリストを受け取り、多項式フィットを行う"""
        pixels = np.array(pixels)
        wavelengths = np.array(wavelengths)
        
        if len(pixels) < 2:
            return None
            
        if len(pixels) == 2:
            # 2点の場合は1次関数 (y = c1*x + c0)
            coeffs = np.polyfit(pixels, wavelengths, 1)
            # 戻り値を c0, c1, c2 の順に揃える (c2は0)
            return coeffs[1], coeffs[0], 0.0
        else:
            # 3点以上の場合は2次関数 (y = c2*x^2 + c1*x + c0)
            coeffs = np.polyfit(pixels, wavelengths, 2)
            # 戻り値を c0, c1, c2 の順に揃える
            return coeffs[2], coeffs[1], coeffs[0]