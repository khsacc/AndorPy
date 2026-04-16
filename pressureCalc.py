class PressureCalculator:
    @staticmethod
    def calculate(sensor, scale, lam, lam0, lam_err=0.0):
        """
        Calculate pressure using an optical pressure sensor
        :param sensor: sensor material (e.g., "Ruby", "Sm2+:SrB4O7")
        :param scale: scale for the pressure calculation
        :param lam: measured peak wavelength (nm)
        :param lam0: zero-pressure peak wavelength (nm)
        :param lam_err: error from fitting
        :return: (pressure [GPa], error [GPa])。If either the sensor or the scale is undefined, the return will be(None, None)
        """
        if sensor == "Ruby":
            if scale == "Piermarini et al. 1975":
                p = 2.740 * (lam - lam0)
                dp = 2.740 * lam_err
                
            elif scale == "Mao et al. hydro 1986":
                A = 1904.0
                B = 7.665
                p = (A / B) * ((lam / lam0)**B - 1.0)
                dp = A * (lam / lam0)**(B - 1.0) * (lam_err / lam0)
                
            elif scale == "Shen et al. 2020":
                A = 1.87 * 10**3
                B = 5.63
                lam_ratio = (lam - lam0) / lam0
                p = A * lam_ratio * (1.0 + B * lam_ratio)
                dp = abs((A / lam0) * (1.0 + 2.0 * B * lam_ratio) * lam_err)
                
            else:
                return None, None
                
            return p, abs(dp)

        elif sensor == "Sm2+:SrB4O7":
            if scale == "Datchi et al. 1997":
                dlam = lam - lam0
                A = 4.032
                B = 9.29e-3
                C = 2.32e-2
                
                p = A * dlam * (1.0 + B * dlam) / (1.0 + C * dlam)
                
                dp_dlam = A * (1.0 + 2.0 * B * dlam + B * C * dlam**2) / ((1.0 + C * dlam)**2)
                dp = abs(dp_dlam * lam_err)
                
                return p, dp
                
            else:
                return None, None

        return None, None

    @staticmethod
    def correct_lambda0(scale, current_t, t0, lam0_at_t0):
        """
        指定されたスケールの温度依存性関数を用いて、現在の温度における lambda0 を計算する
        """
        if scale == "Ragan 1992":
            # 波数 (cm^-1) を計算する式
            def ragan_nu(t):
                return 14423.0 + 4.49e-2 * t - 4.81e-4 * (t**2) + 3.71e-7 * (t**3)
            
            # 波数から波長 (nm) に変換
            def ragan_lam(t):
                nu = ragan_nu(t)
                return 1e7 / nu if nu != 0 else 0.0
                
            lam_t = ragan_lam(current_t)
            lam_t0 = ragan_lam(t0)
            
            # 温度シフトの差分のみを用いて、入力された基準値にオフセットとして加算する
            corrected_lam0 = lam_t - lam_t0 + lam0_at_t0
            return corrected_lam0
            
        elif scale == "Datchi et al. 2007 Linear":
            # ルビーの線形補正 (T <= 600 K を想定)
            return lam0_at_t0 + 7.3e-3 * (current_t - t0)
            
        elif scale == "Datchi et al. 1997":
            # Sm2+:SrB4O7 の温度補正
            # For T <= 500 K, lambda = lambda0.
            # For T > 500 K,  lambda = lambda0 + 1.06*10^-4 * (T-500) + 1.5*10^-7 * (T-500)^2
            def datchi_shift(t):
                if t <= 500.0:
                    return 0.0
                else:
                    dt = t - 500.0
                    return 1.06e-4 * dt + 1.5e-7 * (dt**2)
                    
            shift_current = datchi_shift(current_t)
            shift_t0 = datchi_shift(t0)
            
            return lam0_at_t0 + (shift_current - shift_t0)

        return lam0_at_t0