import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

class DataAnalyzer:
    """リアルタイムスペクトル解析・圧力計算クラス"""
    
    def __init__(self):
        pass

    # ==========================================
    # --- ベース関数群 ---
    # ==========================================
    def gaussian(self, x, a, x0, fwhm, offset):
        """fwhmを用いたガウス関数"""
        return a * np.exp(-4 * np.log(2) * ((x - x0) / fwhm)**2) + offset

    def lorentzian(self, x, a, x0, fwhm, offset):
        """fwhmを用いたローレンツ関数"""
        return a / (1 + 4 * ((x - x0) / fwhm)**2) + offset

    def pseudo_voigt(self, x, a, x0, fwhm, eta, offset):
        """ガウス関数とローレンツ関数を合成したPseudo-Voigt関数"""
        g_val = self.gaussian(x, a, x0, fwhm, offset=0.0)
        l_val = self.lorentzian(x, a, x0, fwhm, offset=0.0)
        return (1 - eta) * g_val + eta * l_val + offset

    def double_gaussian(self, x, a1, x01, fwhm1, a2, x02, fwhm2, offset):
        return self.gaussian(x, a1, x01, fwhm1, 0) + self.gaussian(x, a2, x02, fwhm2, 0) + offset

    def double_lorentzian(self, x, a1, x01, fwhm1, a2, x02, fwhm2, offset):
        return self.lorentzian(x, a1, x01, fwhm1, 0) + self.lorentzian(x, a2, x02, fwhm2, 0) + offset

    def double_pseudo_voigt(self, x, a1, x01, fwhm1, eta1, a2, x02, fwhm2, eta2, offset):
        return self.pseudo_voigt(x, a1, x01, fwhm1, eta1, 0) + self.pseudo_voigt(x, a2, x02, fwhm2, eta2, 0) + offset

    # ==========================================
    # --- フィッティング処理 ---
    # ==========================================
    def fit_spectrum(self, x_data, y_data, func_type="Gauss", fit_start=None, fit_end=None):
        """スペクトルのピークフィッティングを行う（指定されたX軸の範囲内で実行）"""
        
        # 範囲によるマスクの作成
        if fit_start is not None and fit_end is not None:
            start_val = min(fit_start, fit_end)
            end_val = max(fit_start, fit_end)
            mask = (x_data >= start_val) & (x_data <= end_val)
        else:
            mask = np.ones(len(x_data), dtype=bool)

        x_fit = x_data[mask]
        y_fit = y_data[mask]

        if len(x_fit) < 10:
            return None, None, None

        amp_guess = np.max(y_fit) - np.min(y_fit)
        offset_guess = np.min(y_fit)
        x_range = np.max(x_fit) - np.min(x_fit)
        
        # FWHMの初期値はX軸のスケールに依存するため、範囲の2%程度と推測する
        fwhm_guess = x_range * 0.02
        if fwhm_guess <= 0: fwhm_guess = 1.0
        
        res = {}
        
        try:
            # ==========================================
            # --- ダブルピーク関数 ---
            # ==========================================
            if "Double" in func_type:
                peaks, _ = find_peaks(y_fit, distance=5, prominence=amp_guess * 0.1)
                
                if len(peaks) >= 2:
                    top_peaks = sorted(peaks, key=lambda p: y_fit[p], reverse=True)[:2]
                    p1_x = x_fit[top_peaks[0]]
                    p2_x = x_fit[top_peaks[1]]
                    a1_guess = y_fit[top_peaks[0]] - offset_guess
                    a2_guess = y_fit[top_peaks[1]] - offset_guess
                else:
                    max_idx = int(np.argmax(y_fit))
                    p1_x = x_fit[max_idx]
                    p2_x = p1_x + (x_range * 0.1)
                    a1_guess = amp_guess
                    a2_guess = amp_guess * 0.5

                if func_type in ["Double Gauss", "Double Lorentz"]:
                    p0 = [a1_guess, p1_x, fwhm_guess, a2_guess, p2_x, fwhm_guess, offset_guess]
                    bounds = (
                        [0, min(x_fit), 0.0001, 0, min(x_fit), 0.0001, -np.inf],
                        [np.inf, max(x_fit), x_range, np.inf, max(x_fit), x_range, np.inf]
                    )
                elif func_type == "Double pseudo Voigt":
                    p0 = [a1_guess, p1_x, fwhm_guess, 0.5, a2_guess, p2_x, fwhm_guess, 0.5, offset_guess]
                    bounds = (
                        [0, min(x_fit), 0.0001, 0.0, 0, min(x_fit), 0.0001, 0.0, -np.inf],
                        [np.inf, max(x_fit), x_range, 1.0, np.inf, max(x_fit), x_range, 1.0, np.inf]
                    )

                if func_type == "Double Gauss":
                    popt, pcov = curve_fit(self.double_gaussian, x_fit, y_fit, p0=p0, bounds=bounds)
                    y_fit_curve = self.double_gaussian(x_fit, *popt)
                    
                    y1_curve = self.gaussian(x_fit, popt[0], popt[1], popt[2], popt[6])
                    y2_curve = self.gaussian(x_fit, popt[3], popt[4], popt[5], popt[6])
                    
                    p1_pos, p1_w, p2_pos, p2_w = popt[1], popt[2], popt[4], popt[5]
                    perr = np.sqrt(np.diag(pcov))
                    e1_pos, e1_w, e2_pos, e2_w = perr[1], perr[2], perr[4], perr[5]
                    
                elif func_type == "Double Lorentz":
                    popt, pcov = curve_fit(self.double_lorentzian, x_fit, y_fit, p0=p0, bounds=bounds)
                    y_fit_curve = self.double_lorentzian(x_fit, *popt)
                    
                    y1_curve = self.lorentzian(x_fit, popt[0], popt[1], popt[2], popt[6])
                    y2_curve = self.lorentzian(x_fit, popt[3], popt[4], popt[5], popt[6])
                    
                    p1_pos, p1_w, p2_pos, p2_w = popt[1], popt[2], popt[4], popt[5]
                    perr = np.sqrt(np.diag(pcov))
                    e1_pos, e1_w, e2_pos, e2_w = perr[1], perr[2], perr[4], perr[5]
                    
                elif func_type == "Double pseudo Voigt":
                    popt, pcov = curve_fit(self.double_pseudo_voigt, x_fit, y_fit, p0=p0, bounds=bounds)
                    y_fit_curve = self.double_pseudo_voigt(x_fit, *popt)
                    
                    y1_curve = self.pseudo_voigt(x_fit, popt[0], popt[1], popt[2], popt[3], popt[8])
                    y2_curve = self.pseudo_voigt(x_fit, popt[4], popt[5], popt[6], popt[7], popt[8])
                    
                    p1_pos, p1_w, p2_pos, p2_w = popt[1], popt[2], popt[5], popt[6]
                    perr = np.sqrt(np.diag(pcov))
                    e1_pos, e1_w, e2_pos, e2_w = perr[1], perr[2], perr[5], perr[6]
                
                # ピークのX座標が小さい方（左側）を常に Peak1 として返す
                if p1_pos > p2_pos:
                    res = {
                        "is_double": True,
                        "Peak1": p1_pos, "Width1": p1_w, "Peak1_Err": e1_pos, "Width1_Err": e1_w,
                        "Peak2": p2_pos, "Width2": p2_w, "Peak2_Err": e2_pos, "Width2_Err": e2_w,
                        "y_fit1": y1_curve,
                        "y_fit2": y2_curve
                    }
                else:
                    res = {
                        "is_double": True,
                        "Peak1": p2_pos, "Width1": p2_w, "Peak1_Err": e2_pos, "Width1_Err": e2_w,
                        "Peak2": p1_pos, "Width2": p1_w, "Peak2_Err": e1_pos, "Width2_Err": e1_w,
                        "y_fit1": y2_curve,
                        "y_fit2": y1_curve
                    }

            # ==========================================
            # --- シングルピーク関数 ---
            # ==========================================
            else: 
                max_idx = int(np.argmax(y_fit))
                p_x = x_fit[max_idx]
                
                if func_type in ["Gauss", "Lorentz"]:
                    p0 = [amp_guess, p_x, fwhm_guess, offset_guess]
                    bounds = ([0, min(x_fit), 0.0001, -np.inf], [np.inf, max(x_fit), x_range, np.inf])
                elif func_type == "Pseudo Voigt":
                    p0 = [amp_guess, p_x, fwhm_guess, 0.5, offset_guess]
                    bounds = ([0, min(x_fit), 0.0001, 0.0, -np.inf], [np.inf, max(x_fit), x_range, 1.0, np.inf])
                
                if func_type == "Gauss":
                    popt, pcov = curve_fit(self.gaussian, x_fit, y_fit, p0=p0, bounds=bounds)
                    y_fit_curve = self.gaussian(x_fit, *popt)
                elif func_type == "Lorentz":
                    popt, pcov = curve_fit(self.lorentzian, x_fit, y_fit, p0=p0, bounds=bounds)
                    y_fit_curve = self.lorentzian(x_fit, *popt)
                elif func_type == "Pseudo Voigt":
                    popt, pcov = curve_fit(self.pseudo_voigt, x_fit, y_fit, p0=p0, bounds=bounds)
                    y_fit_curve = self.pseudo_voigt(x_fit, *popt)
                
                # すべての関数で popt[1] が位置、popt[2] がFWHMになる
                p_pos, p_w = popt[1], popt[2]
                perr = np.sqrt(np.diag(pcov))
                e_pos, e_w = perr[1], perr[2]
                
                res = {
                    "is_double": False,
                    "Peak": p_pos, "Width": p_w, 
                    "Peak_Err": e_pos, "Width_Err": e_w
                }

            # R2計算
            residuals = y_fit - y_fit_curve
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((y_fit - np.mean(y_fit))**2)
            res["R2"] = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return x_fit, y_fit_curve, res

        except Exception as e:
            print(f"Fitting error ({func_type}): {e}")
            return None, None, None