import os
import sys
import time
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import pylablib
    pylablib.par["devices/dlls/picam"] = r"C:\Program Files\Princeton Instruments\PICam\Runtime"
    from pylablib.devices import PrincetonInstruments 
except ImportError:
    PrincetonInstruments = None

class CameraThreadPI(QThread):
    data_ready = pyqtSignal(str, np.ndarray)
    init_finished = pyqtSignal()
    temperature_ready = pyqtSignal(float)
    
    exposure_set_finished = pyqtSignal()
    temperature_set_finished = pyqtSignal()

    def __init__(self, config=None, debug=False):
        super().__init__()
        self.debug = debug
        self.config=config or {}

        self.thread_active = True
        self.is_measuring = False
        self.cam = None
        
        self.det_width = 1024 
        self.det_height = 1024 

        self.roi_mode = "1d_roi"
        self.roi_vstart = 45
        self.roi_vend = 65
        self.settings_changed = True
        
        self.request_temp = False
        self.new_exposure = None
        self.new_temperature = None
        
        self.mock_exposure = 0.1
        self.mock_temp = -70 # ProEMでよく使われる冷却温度付近

    def run(self):
        try:
            if self.debug or PrincetonInstruments is None:
                print("[DEBUG MODE] Activating dummy camera...")
                self.det_width, self.det_height = 1024, 1024
                time.sleep(1.0)
                self.init_finished.emit()
            else:      
                print("Connecting to Princeton Instruments camera...")
                self.cam = PrincetonInstruments.PicamCamera()

                self.det_width, self.det_height = self.cam.get_detector_size()
                print(f"Connected. Detector size: {self.det_width}x{self.det_height}")
                
                # ProEMの設定初期化
                self.cam.set_exposure(0.1)
                try:
                    # 冷却の設定（PICam APIでの標準的な設定方法）
                    self.cam.set_attribute_value("SensorTemperatureSetPoint", -70.0)
                except Exception as e:
                    print(f"Notice: Could not set default temperature. {e}")

                self.init_finished.emit()
            
            was_measuring = False
            
            while self.thread_active:
                if self.new_exposure is not None:
                    if self.debug:
                        self.mock_exposure = self.new_exposure
                    else:
                        try:
                            self.cam.set_exposure(self.new_exposure)
                        except Exception as e:
                            print(f"Failed to set exposure: {e}")
                    self.new_exposure = None
                    self.exposure_set_finished.emit()

                if self.new_temperature is not None:
                    if self.debug:
                        self.mock_temp = self.new_temperature
                    else:
                        try:
                            self.cam.set_attribute_value("SensorTemperatureSetPoint", float(self.new_temperature))
                        except Exception as e:
                            print(f"Failed to set temperature: {e}")
                    self.new_temperature = None
                    self.temperature_set_finished.emit()

                if self.request_temp:
                    if self.debug:
                        self.temperature_ready.emit(self.mock_temp + np.random.uniform(-0.5, 0.5))
                    else:
                        try:
                            # 現在の温度を読み取る
                            temp = self.cam.get_attribute_value("SensorTemperatureReading")
                            self.temperature_ready.emit(temp)
                        except Exception as e:
                            self.temperature_ready.emit(-999.0)
                    self.request_temp = False

                if self.is_measuring:
                    if not was_measuring:
                        was_measuring = True

                    if self.settings_changed:
                        if not self.debug:
                            self._apply_camera_settings()
                        self.settings_changed = False

                    if self.debug:
                        # デバッグ用ダミーデータ生成
                        x = np.arange(self.det_width)
                        y1 = 500 * np.exp(-((x - 700)**2) / (2 * 4**2))
                        y2 = 250 * np.exp(-((x - 675)**2) / (2 * 4**2))
                        base = 100 + np.random.normal(0, 10, self.det_width)
                        spectrum = y1 + y2 + base
                        
                        if self.roi_mode == "2d":
                            data = np.tile(spectrum, (self.det_height, 1))
                            self.data_ready.emit("2d", data)
                        else:
                            self.data_ready.emit("1d", spectrum)
                            
                        time.sleep(self.mock_exposure) 
                    else:
                        # 実機でのデータ取得
                        data = self.cam.snap()
                        if self.roi_mode == "2d":
                            self.data_ready.emit("2d", data)
                        else:
                            # ハードウェアビニングされていない場合、ソフトウェアで積算
                            if data.ndim == 2:
                                spectrum = np.sum(data, axis=0)
                            else:
                                spectrum = data
                            self.data_ready.emit("1d", spectrum)
                else:
                    was_measuring = False
                    time.sleep(0.05)
                
        except Exception as e:
            print(f"An error occurred in the camera thread: {e}")
        finally:
            if self.cam is not None:
                self.cam.close()
                self.cam = None

    def read_temperature(self):
        self.request_temp = True

    def update_exposure(self, exp_time):
        self.new_exposure = exp_time

    def update_temperature(self, temp):
        self.new_temperature = temp

    def _apply_camera_settings(self):
        if self.cam is None: return
        # pylablibの汎用ROI設定メソッド (hstart, hend, vstart, vend, hbin, vbin)
        try:
            if self.roi_mode == "2d":
                self.cam.set_roi(0, self.det_width, 0, self.det_height, hbin=1, vbin=1)
            elif self.roi_mode == "1d_full":
                self.cam.set_roi(0, self.det_width, 0, self.det_height, hbin=1, vbin=self.det_height)
            elif self.roi_mode == "1d_roi":
                v_size = self.roi_vend - self.roi_vstart
                if v_size > 0:
                    self.cam.set_roi(0, self.det_width, self.roi_vstart, self.roi_vend, hbin=1, vbin=v_size)
        except Exception as e:
            print(f"Failed to apply ROI settings: {e}")

    def update_roi_settings(self, mode, vstart=0, vend=256):
        self.roi_mode = mode
        self.roi_vstart = vstart
        self.roi_vend = vend
        self.settings_changed = True
    
    def get_temperature(self):
        return self.mock_temp if self.debug else (self.new_temperature if self.new_temperature is not None else -70.0)

    @property
    def camera(self):
        return self

    def acquire_single_image(self, acq_time=None):
        if acq_time is not None:
            self.update_exposure(acq_time)
            time.sleep(0.1)

        if self.debug:
            x = np.arange(self.det_width)
            y1 = 500 * np.exp(-((x - 700)**2) / (2 * 4**2))
            y2 = 250 * np.exp(-((x - 675)**2) / (2 * 4**2))
            base = 100 + np.random.normal(0, 10, self.det_width)
            spectrum = y1 + y2 + base
            
            if self.roi_mode == "2d":
                return np.tile(spectrum, (self.det_height, 1))
            else:
                return spectrum
        else:
            if self.cam is None: return None
            
            if self.settings_changed:
                self._apply_camera_settings()
                self.settings_changed = False
                
            try:
                data = self.cam.snap()
                return data
            except Exception as e:
                print(f"Failed to acquire single image: {e}")
                return None

    def start_measuring(self):
        self.is_measuring = True

    def stop_measuring(self):
        self.is_measuring = False

    def stop_thread(self):
        self.thread_active = False
        self.wait()