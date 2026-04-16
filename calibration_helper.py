import numpy as np
from PyQt6.QtWidgets import QDialog, QVBoxLayout
from PyQt6.QtCore import Qt
import pyqtgraph as pg

class ReferenceHelperWindow(QDialog):
    def __init__(self, json_data, is_raman=False, laser_wl=532.0, parent=None):
        super().__init__(parent)
        
        material = json_data.get("material", "Reference")
        approx = json_data.get("approximate_range", "Unknown")
        self.setWindowTitle(f"Guide: {material} around {approx} nm")
        self.resize(800, 500)
        
        self.json_data = json_data
        self.is_raman = is_raman
        self.laser_wl = laser_wl
        
        self.init_ui()

    def nm_to_raman(self, wl_nm):
        """Wavelength (nm) to Raman Shift (cm^-1)"""
        if wl_nm == 0: 
            return 0.0
        # Formula: (1e7 / exc_wl) - (1e7 / wl)
        return (1e7 / self.laser_wl) - (1e7 / wl_nm)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        # グリッドを削除 (Falseに変更)
        self.plot_widget.showGrid(x=False, y=False)
        
        spectrum = self.json_data.get("spectrum", {})
        x_wl = np.array(spectrum.get("wavelength", []))
        y_int = np.array(spectrum.get("intensity", []))
        
        if len(x_wl) == 0:
            layout.addWidget(self.plot_widget)
            return

        if self.is_raman:
            # WavelengthをRaman Shiftに変換
            x_plot = np.array([self.nm_to_raman(val) for val in x_wl])
            self.plot_widget.setLabel('bottom', 'Raman Shift (cm⁻¹)')
        else:
            x_plot = x_wl
            self.plot_widget.setLabel('bottom', 'Wavelength (nm)')
            
        self.plot_widget.setLabel('left', 'Intensity')
        
        # スペクトルのプロット
        self.plot_widget.plot(x_plot, y_int, pen=pg.mkPen('k', width=1.5))
        
        ref_peaks = self.json_data.get("reference_peaks", [])
        max_y = np.max(y_int) if len(y_int) > 0 else 1.0
        
        for peak in ref_peaks:
            calib_nm = peak.get("calibrated")
            lit_val = peak.get("literature")
            
            if calib_nm is None or lit_val is None: 
                continue
            
            pos_x = self.nm_to_raman(calib_nm) if self.is_raman else calib_nm
            
            # 縦線（点線）の描画
            line = pg.InfiniteLine(pos=pos_x, angle=90, pen=pg.mkPen('r', style=Qt.PenStyle.DashLine))
            self.plot_widget.addItem(line)
            
            # テキストラベル（JSONの桁数そのまま表示、-90度回転）
            # anchorのY要素を 0.8 などに微調整して、点線と文字の隙間を少し短くする
            label_text = str(lit_val)
            text_item = pg.TextItem(text=label_text, color='r', angle=-90, anchor=(0, 0.8))
            
            # グラフの上部に配置
            text_item.setPos(pos_x, max_y * 0.95)
            self.plot_widget.addItem(text_item)
            
        layout.addWidget(self.plot_widget)