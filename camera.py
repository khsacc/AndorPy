import time
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

# ダミーモード時はエラーを回避するためtry-exceptで囲む
try:
    from pylablib.devices import Andor
except ImportError:
    Andor = None

class CameraThread(QThread):
    data_ready = pyqtSignal(str, np.ndarray)
    init_finished = pyqtSignal()
    temperature_ready = pyqtSignal(float)
    
    exposure_set_finished = pyqtSignal()
    temperature_set_finished = pyqtSignal()

    def __init__(self, debug=False):
        super().__init__()
        self.debug = debug
        self.thread_active = True
        self.is_measuring = False
        self.cam = None
        
        self.det_width = 1024 
        self.det_height = 127 

        self.roi_mode = "1d_roi"
        self.roi_vstart = 45
        self.roi_vend = 65
        self.settings_changed = True
        
        self.request_temp = False
        self.new_exposure = None
        self.new_temperature = None
        
        # デバッグ用の仮想設定値
        self.mock_exposure = 0.1
        self.mock_temp = -60.0

    def run(self):
        try:
            if self.debug:
                print("[DEBUG MODE] Activating dummy camera...")
                self.det_width, self.det_height = 1024, 127
                time.sleep(1.0) # 初期化を模倣
                self.init_finished.emit()
            else:
                print("Connecting to camera and initializing cooler...")
                self.cam = Andor.AndorSDK2Camera()
                self.det_width, self.det_height = self.cam.get_detector_size()
                print(f"Connected to Andor camera. Detector size: {self.det_width}x{self.det_height}")
                self.cam.set_temperature(-60)
                self.cam.set_cooler(True)
                self.cam.set_exposure(0.1) 
                self.init_finished.emit()
            
            was_measuring = False
            
            while self.thread_active:
                if self.new_exposure is not None:
                    if self.debug:
                        self.mock_exposure = self.new_exposure
                        print(f"[DEBUG] Exposure set to {self.mock_exposure} s")
                    else:
                        try:
                            self.cam.set_exposure(self.new_exposure)
                            print(f"Exposure set to {self.new_exposure} s")
                        except Exception as e:
                            print(f"Failed to set exposure: {e}")
                    self.new_exposure = None
                    self.exposure_set_finished.emit()

                if self.new_temperature is not None:
                    if self.debug:
                        self.mock_temp = self.new_temperature
                        print(f"[DEBUG] Target temperature set to {self.mock_temp} C")
                    else:
                        try:
                            self.cam.set_temperature(self.new_temperature)
                            print(f"Target temperature set to {self.new_temperature} C")
                        except Exception as e:
                            print(f"Failed to set temperature: {e}")
                    self.new_temperature = None
                    self.temperature_set_finished.emit()

                if self.request_temp:
                    if self.debug:
                        # デバッグ時は指定温度にゆらぎを持たせて返す
                        self.temperature_ready.emit(self.mock_temp + np.random.uniform(-0.5, 0.5))
                    else:
                        try:
                            temp = self.cam.get_temperature()
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
                        # === デバッグ用ダミーデータ生成 ===
                        x = np.arange(self.det_width)
                        # ルビーのR1, R2線を模したダブルピーク + 背景ノイズ
                        y1 = 500 * np.exp(-((x - 700)**2) / (2 * 4**2))
                        y2 = 250 * np.exp(-((x - 675)**2) / (2 * 4**2))
                        base = 100 + np.random.normal(0, 10, self.det_width)
                        spectrum = y1 + y2 + base
                        
                        if self.roi_mode == "2d":
                            data = np.tile(spectrum, (self.det_height, 1))
                            self.data_ready.emit("2d", data)
                        else:
                            self.data_ready.emit("1d", spectrum)
                            
                        time.sleep(self.mock_exposure) # 露光時間分待機
                    else:
                        data = self.cam.snap()
                        if self.roi_mode == "2d":
                            self.data_ready.emit("2d", data)
                        else:
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
        if self.roi_mode == "2d":
            self.cam.set_roi(0, self.det_width, 0, self.det_height, hbin=1, vbin=1)
        elif self.roi_mode == "1d_full":
            self.cam.set_roi(0, self.det_width, 0, self.det_height, hbin=1, vbin=self.det_height)
        elif self.roi_mode == "1d_roi":
            v_size = self.roi_vend - self.roi_vstart
            if v_size > 0:
                self.cam.set_roi(0, self.det_width, self.roi_vstart, self.roi_vend, hbin=1, vbin=v_size)

    def update_roi_settings(self, mode, vstart=0, vend=256):
        self.roi_mode = mode
        self.roi_vstart = vstart
        self.roi_vend = vend
        self.settings_changed = True

    def start_measuring(self):
        self.is_measuring = True

    def stop_measuring(self):
        self.is_measuring = False

    def stop_thread(self):
        self.thread_active = False
        self.wait()