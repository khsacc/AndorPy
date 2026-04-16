import numpy as np

class PressureCalculator:
    # センサーごとの初期値（ゼロ圧力ピーク）
    INITIAL_VALUES = {
        "Ruby": 694.300,
        "Sm2+:SrB4O7": 685.410,
        "13C diamond 1st order": 1333.00,
        "Cubic BN": 1054.00,
        "Zircon v3(SiO4)": 1008.00
    }

    # センサーごとに温度スケールの有効範囲を管理
    TEMP_VALID_RANGES = {
        "Ruby": {
            "Ragan et al. 1992": (0.0, 600.0),
            "Datchi et al. 2007": (290, 800) 
        },
        "Sm2+:SrB4O7": {
            "Datchi et al. 2007": (290, 900.0)
        },
        "13C diamond 1st order": {
            "Schiferl et al. 1997": (290, 1500.0)
        }
        # 他のセンサーやスケールも同様に追加可能
    }

    @staticmethod
    def is_temp_in_range(sensor, t_scale, temp):
        """センサーと温度スケールの組み合わせから範囲内か判定"""
        # 親（センサー）が存在するか
        if sensor not in PressureCalculator.TEMP_VALID_RANGES:
            return True, (None, None)
        
        # 子（温度スケール）が存在するか
        s_dict = PressureCalculator.TEMP_VALID_RANGES[sensor]
        if t_scale not in s_dict:
            return True, (None, None)
            
        rng = s_dict[t_scale]
        is_valid = rng[0] <= temp <= rng[1]
        return is_valid, rng

    @staticmethod
    def calculate(sensor, p_scale, lam, lam0, lam_err=0.0, current_t=298.15, t0=298.15):
        try:
            # --- 13C Diamond (Schiferl 1997) ---
            if sensor == "13C diamond 1st order" and p_scale == "Schiferl et al. 1997":
                # ダミー計算式
                p = 0.354 * (lam - (1333.0 - 0.025 * (current_t - t0)))
                return p, 0.354 * lam_err

            # --- Ruby Scales ---
            if sensor == "Ruby":
                if p_scale == "Piermarini et al. 1975":
                    p = 2.746 * (lam - lam0)
                    return p, 2.746 * lam_err
                elif p_scale == "Mao et al. 1986":
                    A, B = 1904.0, 7.665
                    dlam = lam - lam0
                    p = (A / B) * (((dlam / lam0)+1)**B - 1.0)
                    dp = A * (lam / lam0)**(B - 1.0) * (lam_err / lam0) # 要確認！
                    return p, dp
                elif p_scale == "Shen et al. 2020":
                    A, B = 1870.0, 5.63
                    ratio = (lam - lam0) / lam0
                    p = A * ratio * (1.0 + B * ratio)
                    dp = A * (lam_err / lam0) * (1.0 + 2.0 * B * ratio) # 要確認！
                    return p, dp

            # --- Sm2+:SrB4O7 ---
            if sensor == "Sm2+:SrB4O7":
                if p_scale == "Datchi 1997":
                    dlam = lam - lam0
                    p = 4.032 * dlam * (1+9.29 * 10**-3 * dlam) / (1+2.32 * 10 ** -2 * dlam) 
                    return p, lam_err # Todo: 誤差の計算

            # その他
            if sensor == "Cubic BN": return 0.45 * (lam - lam0), 0.0
            if sensor == "Zircon v3(SiO4)": return 0.58 * (lam - lam0), 0.0

            return None, None
        except:
            return None, None

    @staticmethod
    def get_corrected_lam0(sensor, t_scale, current_t, t0, lam0_at_t0):
        if sensor == "Ruby":
            if t_scale == "Ragan et al. 1992":
                shift = 0.007 * (current_t - t0)
                return lam0_at_t0 + shift
            elif t_scale == "Datchi et al. 2007":
                return lam0_at_t0 + 0.0073 * (current_t - t0)
        if sensor == "Sm2+:SrB4O7": 
            return None
        return lam0_at_t0