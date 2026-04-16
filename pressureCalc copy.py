import math

class PressureCalculator:
    @staticmethod
    def calculate_from_wavelength(sensor, scale, temperature_scale, lam, lam0, lam_err=0.0, consider_temprature=False, current_t=298.15, t0=298.15):
        """
        Calculate pressure using an optical pressure sensor
        :param sensor: sensor material (e.g., "Ruby", "Sm2+:SrB4O7", "13C diamond 1st order")
        :param scale: scale for the pressure calculation
        :param lam: measured peak wavelength (nm) or Raman shift (cm-1)
        :param lam0: zero-pressure peak wavelength or Raman shift at current T
        :param lam_err: error from fitting
        :param current_t: current temperature (K), needed for some scales
        :return: (pressure [GPa], error [GPa]). If undefined, return (None, None)
        """
        if sensor == "Ruby":
            
            def calculate_lambda_zero_ruby(consider_temperature, temperature_scale, lam0, current_t, t0):
                if not consider_temperature:
                    return lam0
                else:
                    if temperature_scale == "Ragan et al. 1992":
                        def ragan_nu(t):
                            return 14423.0 + 4.49e-2 * t - 4.81e-4 * (t**2) + 3.71e-7 * (t**3)
                        def ragan_lam(t):
                            nu = ragan_nu(t)
                            return 1e7 / nu if nu != 0 else 0.0
                            
                        lam_t = ragan_lam(current_t)
                        lam_t0 = ragan_lam(t0)
                        return lam_t - lam_t0 + lam0_at_t0     

            if scale == "Piermarini et al. 1975":
                p = 2.740 * (lam - lam0)
                dp = 2.740 * lam_err
                return p, abs(dp)
                
            elif scale == "Mao et al. hydro 1986":
                A = 1904.0
                B = 7.665
                p = (A / B) * ((lam / lam0)**B - 1.0)
                dp = A * (lam / lam0)**(B - 1.0) * (lam_err / lam0)
                return p, abs(dp)
                
            elif scale == "Shen et al. 2020":
                A = 1.87 * 10**3
                B = 5.63
                lam_ratio = (lam - lam0) / lam0
                p = A * lam_ratio * (1.0 + B * lam_ratio)
                dp = abs((A / lam0) * (1.0 + 2.0 * B * lam_ratio) * lam_err)
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

        elif sensor == "13C diamond 1st order":
            if scale == "Schiferl et al. 1997":
                p = (lam - lam0) / 2.83
                dp = lam_err / 2.83
                return p, abs(dp)
            elif scale == "Mysen and Yamashita 2010":
                p = 1000 * (lam - lam0) / 0.002707
                dp = 1000 * lam_err / 0.002707
                return p, abs(dp)
            elif scale == "Munsch et al. 2015":
                inner = 510.41 + lam0 - lam
                if inner < 0:
                    return None, None
                p = 373.97 - 16.55 * math.sqrt(inner)
                dp = abs((16.55 / (2 * math.sqrt(inner))) * lam_err) if inner > 0 else 0
                return p, dp

        elif sensor == "Cubic BN":
            if scale == "Datchi et al. 2004":
                a = -9.3e-3
                b = -1.54e-5
                c0 = 3.07
                c1 = 1.25e-3
                c2 = -1.03e-6
                d = -0.0103
                
                A_T = c0 + c1 * current_t + c2 * current_t**2
                inner = A_T**2 + 4 * d * (lam - lam0)
                if inner < 0:
                    return None, None
                
                p = -1/(2*d) * (A_T + math.sqrt(inner))
                dp = abs((-1 / math.sqrt(inner)) * lam_err) if inner > 0 else 0
                return p, dp

        elif sensor == "Zircon ν3(SiO4)":
            if scale == "Schmidt et al. 2013":
                p = (lam - lam0) / 5.69
                dp = lam_err / 5.69
                return p, abs(dp)

        return None, None

    @staticmethod
    def correct_lambda0(scale, current_t, t0, lam0_at_t0):
        """
        指定されたスケールの温度依存性関数を用いて、現在の温度における lambda0 (または nu0) を計算する
        """

            
        if scale == "Datchi et al. 2007 Linear":
            return lam0_at_t0 + 7.3e-3 * (current_t - t0)
            
        elif scale == "Datchi et al. 1997":
            def datchi_shift(t):
                if t <= 500.0:
                    return 0.0
                else:
                    dt = t - 500.0
                    return 1.06e-4 * dt + 1.5e-7 * (dt**2)
            return lam0_at_t0 + (datchi_shift(current_t) - datchi_shift(t0))
            
        elif scale == "Schiferl et al. 1997":
            def schiferl_shift(t):
                if t > 1500: t = 1500
                if t >= 200:
                    return 0.450 - 7.36e-4 * ((t - 200)**1.5)
                else:
                    return 0.450
            return lam0_at_t0 + (schiferl_shift(current_t) - schiferl_shift(t0))
            
        elif scale == "Mysen and Yamashita 2010":
            t = current_t - 273.15
            return lam0_at_t0 - (1.065e-2 * t + 1.769e-5 * t**2)
            
        elif scale == "Munsch et al. 2015":
            return lam0_at_t0 + 6.9e-3 * current_t - 2.32e-5 * current_t**2
            
        elif scale == "Datchi et al. 2004":
            a = -9.3e-3
            b = -1.54e-5
            return lam0_at_t0 + a * current_t + b * current_t**2
            
        elif scale == "Schmidt et al. 2013":
            def schmidt_nu(temp):
                t = temp - 273.15
                return 7.54e-9 * t**3 - 1.61e-5 * t**2 - 2.89e-2 * t + 1008.9
            return lam0_at_t0 + (schmidt_nu(current_t) - schmidt_nu(t0))

        return lam0_at_t0