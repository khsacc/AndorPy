class PressureCalculator:
    @staticmethod
    def calculate(sensor, scale, lam, lam0, lam_err=0.0):
        """
        ルビー蛍光等の波長から圧力を計算する
        :param sensor: センサー物質名 (例: "Ruby")
        :param scale: 圧力計算のスケール名
        :param lam: 測定された波長 (nm)
        :param lam0: 常圧での波長 (nm)
        :param lam_err: フィッティングから得られた波長の誤差
        :return: (圧力[GPa], 誤差[GPa]) のタプル。未定義のセンサー・スケールの場合は(None, None)
        """
        if sensor != "Ruby":
            return None, None
            
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
            
        return lam0_at_t0