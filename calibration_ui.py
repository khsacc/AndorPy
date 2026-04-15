import json
import os
from datetime import datetime
import numpy as np
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem,
                             QCheckBox, QComboBox, QHeaderView, QWidget, 
                             QAbstractSpinBox, QDoubleSpinBox, QSplitter,
                             QScrollArea, QRadioButton, QFileDialog, QMessageBox, QSlider)
from PyQt6.QtCore import Qt
import pyqtgraph as pg

from calibration import CalibrationCore

class CustomDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    def wheelEvent(self, event):
        event.ignore()

class CalibrationWindow(QDialog):
    def __init__(self, camera_thread=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wavelength Calibration")
        self.resize(1100, 750)
        
        self.setStyleSheet("""
            QWidget { color: #000000; }
            QDialog { background-color: #FAFAFA; }
            QLabel { color: #000000; font-size: 13px; }
            QGroupBox { font-weight: bold; color: #000000; }
            QTableWidget { background-color: #FFFFFF; color: #000000; alternate-background-color: #F0F0F0; }
            QHeaderView::section { background-color: #E0E0E0; font-weight: bold; color: #000000; }
            QRadioButton { color: #000000; }
            QCheckBox { color: #000000; }
            QPushButton { background-color: #E0E0E0; color: #000000; border: 1px solid #999; border-radius: 3px; }
            QPushButton:hover { background-color: #D0D0D0; }
            QComboBox { background-color: #FFFFFF; color: #000000; border: 1px solid #999; }
            QComboBox QAbstractItemView { background-color: #FFFFFF; color: #000000; selection-background-color: #2196F3; selection-color: #FFFFFF; }
            QDoubleSpinBox { background-color: #FFFFFF; color: #000000; border: 1px solid #999; }
            QSpinBox { background-color: #FFFFFF; color: #000000; border: 1px solid #999; }
        """)
        
        self.camera_thread = camera_thread
        self.calib_core = CalibrationCore()
        
        self.current_spectrum = None
        self.peak_lines = []
        self.peak_texts = []
        self.is_acquiring = False
        
        self.calib_coeffs = None 
        self.row_widgets = []
        
        self.init_ui()
        
        # Main UIの設定から初期単位を合わせる
        main_window = self.parent()
        if main_window and main_window.radio_spec_mode_raman.isChecked():
            self.radio_unit_raman.setChecked(True)
        else:
            self.radio_unit_wl.setChecked(True)
        self.update_table_header()
        
        if self.camera_thread:
            self.camera_thread.data_ready.connect(self.on_data_ready)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        plot_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("Full Spectrum", color='k')
        self.plot_widget.setBackground('w')
        self.plot_widget.getAxis('bottom').setPen('k')
        self.plot_widget.getAxis('left').setPen('k')
        self.plot_widget.setLabel('left', 'Intensity (Counts)', color='k')
        self.plot_widget.setLabel('bottom', 'Pixel', color='k')
        self.plot_widget.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.plot_scatter = self.plot_widget.plot(pen=None, symbol='o', symbolSize=3, symbolBrush='b')
        plot_splitter.addWidget(self.plot_widget)
        
        self.bottom_scroll = QScrollArea()
        self.bottom_scroll.setFixedHeight(220)
        self.bottom_scroll.setWidgetResizable(True)
        self.bottom_content = QWidget()
        self.bottom_content.setStyleSheet("background-color: #FFFFFF;")
        self.bottom_layout = QHBoxLayout(self.bottom_content)
        self.bottom_scroll.setWidget(self.bottom_content)
        plot_splitter.addWidget(self.bottom_scroll)
        
        plot_splitter.setStretchFactor(0, 3)
        plot_splitter.setStretchFactor(1, 1)
        main_layout.addWidget(plot_splitter, stretch=2)
        
        controls_layout = QVBoxLayout()
        
        self.btn_acquire = QPushButton("Acquire a spectrum")
        self.btn_acquire.clicked.connect(self.acquire_spectrum)
        self.btn_acquire.setStyleSheet("font-weight: bold; padding: 5px;")
        
        acq_time_layout = QHBoxLayout()
        acq_time_layout.addWidget(QLabel("Acquisition time (s):"))
        self.spin_acq_time = CustomDoubleSpinBox()
        self.spin_acq_time.setRange(0.001, 3600)
        self.spin_acq_time.setValue(0.1)
        self.spin_acq_time.setDecimals(3)
        self.spin_acq_time.editingFinished.connect(self.update_acq_time)
        acq_time_layout.addWidget(self.spin_acq_time)

        # --- Unit Selection (Wavelength vs Raman Shift) ---
        unit_layout = QHBoxLayout()
        self.radio_unit_wl = QRadioButton("Wavelength (nm)")
        self.radio_unit_raman = QRadioButton("Raman shift (cm⁻¹)")
        self.radio_unit_wl.setChecked(True)
        self.radio_unit_wl.toggled.connect(self.update_table_header)
        self.radio_unit_raman.toggled.connect(self.update_table_header)
        unit_layout.addWidget(QLabel("Calibration Unit:"))
        unit_layout.addWidget(self.radio_unit_wl)
        unit_layout.addWidget(self.radio_unit_raman)
        unit_layout.addStretch()
        # ------------------------------------------------
        
        find_peaks_layout = QHBoxLayout()
        self.btn_find_peaks = QPushButton("Find peaks")
        self.btn_find_peaks.clicked.connect(self.find_peaks)
        self.btn_find_peaks.setStyleSheet("padding: 5px;")
        
        slider_layout = QVBoxLayout()
        slider_label = QLabel("Threshold:")
        self.slider_threshold = QSlider(Qt.Orientation.Horizontal)
        self.slider_threshold.setRange(10, 100) 
        self.slider_threshold.setValue(75)
        self.slider_threshold.setToolTip("Adjust peak finding threshold")
        
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.slider_threshold)
        
        find_peaks_layout.addWidget(self.btn_find_peaks)
        find_peaks_layout.addLayout(slider_layout)

        neon_layout = QHBoxLayout()
        neon_layout.addWidget(QLabel("Import neon peaks around 694 nm:"))
        self.radio_neon_yes = QRadioButton("Yes")
        self.radio_neon_no = QRadioButton("No")
        self.radio_neon_yes.setChecked(True)
        self.radio_neon_yes.toggled.connect(self.update_table_value_widgets)
        self.radio_neon_no.toggled.connect(self.update_table_value_widgets)
        neon_layout.addWidget(self.radio_neon_yes)
        neon_layout.addWidget(self.radio_neon_no)
        
        self.table = QTableWidget(0, 3)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.update_table_header()
        
        self.btn_calibrate = QPushButton("Calibrate")
        self.btn_calibrate.clicked.connect(self.calibrate)
        self.btn_calibrate.setStyleSheet("font-weight: bold; color: white; background-color: #2196F3; padding: 8px; border: none;")
        
        self.lbl_calib_result = QLabel("y = c0 + c1*x + c2*x^2\nc0 = ...\nc1 = ...\nc2 = ...")
        self.lbl_calib_result.setStyleSheet("font-family: Consolas; background-color: #EEEEEE; padding: 10px; border: 1px solid #CCC; color: #000000;")
        
        self.btn_save_apply = QPushButton("Save and apply")
        self.btn_save_apply.setEnabled(False) 
        self.btn_save_apply.clicked.connect(self.save_and_apply)
        
        controls_layout.addWidget(self.btn_acquire)
        controls_layout.addLayout(acq_time_layout)
        controls_layout.addLayout(unit_layout) # 追加したユニットレイアウト
        controls_layout.addLayout(find_peaks_layout)
        controls_layout.addLayout(neon_layout)
        controls_layout.addWidget(self.table)
        controls_layout.addWidget(self.btn_calibrate)
        controls_layout.addWidget(self.lbl_calib_result)
        controls_layout.addWidget(self.btn_save_apply)
        
        main_layout.addLayout(controls_layout, stretch=1)
        
    def update_table_header(self):
        unit_str = "nm" if self.radio_unit_wl.isChecked() else "cm⁻¹"
        self.table.setHorizontalHeaderLabels(["Peak pos. (px)", "Use", f"Value ({unit_str})"])

    def update_acq_time(self):
        if self.camera_thread:
            self.camera_thread.update_exposure(self.spin_acq_time.value())
            
    def acquire_spectrum(self):
        if self.camera_thread:
            self.update_acq_time()
            self.is_acquiring = True
            self.btn_acquire.setEnabled(False)
            self.btn_acquire.setText("Acquiring...")
            self.camera_thread.start_measuring()
            
    def on_data_ready(self, mode, data):
        if self.is_acquiring and mode == "1d":
            if self.parent() and self.parent().chk_flip_x.isChecked():
                data = data[::-1]
                
            self.current_spectrum = data
            self.plot_scatter.setData(data)
            self.camera_thread.stop_measuring()
            self.is_acquiring = False
            self.btn_acquire.setEnabled(True)
            self.btn_acquire.setText("Acquire a spectrum")
            
            self.find_peaks()
            
    def find_peaks(self):
        if self.current_spectrum is None:
            return
            
        threshold_mult = self.slider_threshold.value() / 10.0
        fitted_peaks = self.calib_core.find_and_fit_peaks(self.current_spectrum, prominence_multiplier=threshold_mult)
        
        self.table.setRowCount(0)
        self.row_widgets.clear()
        
        for item in self.peak_lines + self.peak_texts:
            self.plot_widget.removeItem(item)
        self.peak_lines.clear()
        self.peak_texts.clear()
        
        while self.bottom_layout.count():
            child = self.bottom_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        max_y = np.max(self.current_spectrum)
        
        for i, p_data in enumerate(fitted_peaks):
            center = p_data["center"]
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            pos_item = QTableWidgetItem(f"{center:.2f}")
            pos_item.setFlags(pos_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, pos_item)
            
            chk = QCheckBox()
            chk.setChecked(False) 
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.addWidget(chk)
            self.table.setCellWidget(row, 1, chk_widget)
            
            self.row_widgets.append({"check": chk, "input": None, "px": center})
            
            # Useボタンがトグルされたら入力ウィジェットを生成する
            chk.stateChanged.connect(lambda state, r=row: self.on_use_toggled(state, r))
            
            line = pg.InfiniteLine(pos=center, angle=90, pen=pg.mkPen('r', style=Qt.PenStyle.DashLine))
            text = pg.TextItem(f"#{i+1}", color='r', anchor=(0, 1))
            text.setPos(center, max_y * 0.95)
            self.plot_widget.addItem(line)
            self.plot_widget.addItem(text)
            self.peak_lines.append(line)
            self.peak_texts.append(text)
            
            small_plot = pg.PlotWidget()
            small_plot.setTitle(f"Peak #{i+1}", color='k')
            small_plot.setBackground('w')
            small_plot.getAxis('bottom').setPen('k')
            small_plot.getAxis('left').setPen('k')
            small_plot.setFixedSize(180, 180)
            small_plot.plot(p_data["x_fit"], p_data["y_data"], pen=None, symbol='o', symbolSize=3, symbolBrush='b')
            small_plot.plot(p_data["x_fit"], p_data["y_curve"], pen=pg.mkPen('r', width=2))
            
            self.bottom_layout.addWidget(small_plot)
            
        self.bottom_layout.addStretch()

    def create_value_widget_for_row(self, row):
        if self.radio_neon_yes.isChecked():
            val_widget = QComboBox()
            # Neon peaks around 694 nm
            val_widget.addItems(["692.94673", "702.40504", "703.24131"])
        else:
            val_widget = CustomDoubleSpinBox()
            val_widget.setRange(-10000, 20000)
            val_widget.setDecimals(5)
            
        self.table.setCellWidget(row, 2, val_widget)
        if row < len(self.row_widgets):
            self.row_widgets[row]["input"] = val_widget

    def on_use_toggled(self, state, row):
        is_checked = (state == Qt.CheckState.Checked.value)
        if is_checked:
            self.create_value_widget_for_row(row)
        else:
            self.table.removeCellWidget(row, 2)
            if row < len(self.row_widgets):
                self.row_widgets[row]["input"] = None

    def update_table_value_widgets(self):
        for row in range(self.table.rowCount()):
            chk_widget = self.table.cellWidget(row, 1)
            if chk_widget:
                chk = chk_widget.layout().itemAt(0).widget()
                if chk.isChecked():
                    self.create_value_widget_for_row(row)

    def calibrate(self):
        pixels = []
        ref_values = []
        
        for row_data in self.row_widgets:
            if row_data["check"].isChecked() and row_data["input"] is not None:
                px = row_data["px"]
                input_widget = row_data["input"]
                
                if isinstance(input_widget, QComboBox):
                    wl = float(input_widget.currentText())
                else:
                    wl = input_widget.value()
                    
                pixels.append(px)
                ref_values.append(wl)
                
        if len(pixels) < 2:
            self.calib_coeffs = None
            self.lbl_calib_result.setText("Please check and provide values\nfor at least 2 peaks.")
            self.btn_save_apply.setEnabled(False)
            return
            
        coeffs_dict = self.calib_core.calibrate(pixels, ref_values)
        if coeffs_dict is not None:
            self.calib_coeffs = (coeffs_dict["c0"], coeffs_dict["c1"], coeffs_dict["c2"])
            self.lbl_calib_result.setText(
                f"y = c0 + c1*x + c2*x^2\n"
                f"c0 = {coeffs_dict['c0']:.6e}\n"
                f"c1 = {coeffs_dict['c1']:.6e}\n"
                f"c2 = {coeffs_dict['c2']:.6e}"
            )
            self.btn_save_apply.setEnabled(True)
        else:
            self.calib_coeffs = None
            self.lbl_calib_result.setText("Calibration failed.")
            self.btn_save_apply.setEnabled(False)

    def save_and_apply(self):
        if self.calib_coeffs is None:
            return
            
        main_window = self.parent()
        if main_window is None:
            return
            
        grating = main_window.combo_grating.currentText()
        center_wl = main_window.spin_centre_wl.value()
        
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        unit_str = "Wavelength" if self.radio_unit_wl.isChecked() else "Raman shift"
        unit_sym = "nm" if self.radio_unit_wl.isChecked() else "cm-1"
        
        default_filename = f"config_grating{grating}_centre{center_wl}{unit_sym}_{date_str}.json"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Configuration Data", 
            default_filename, 
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        if main_window.radio_2d.isChecked():
            mode = "2D Image View"
        elif main_window.radio_1d_full.isChecked():
            mode = "1D Spectrum (Full Range Binning)"
        else:
            mode = "1D Spectrum (Custom ROI)"
            
        roi_start = main_window.spin_vstart.value()
        roi_end = main_window.spin_vend.value()
        
        c0, c1, c2 = self.calib_coeffs
        
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "spectrometer_settings": {
                "grating_grooves_per_mm": grating,
                "center_value": center_wl,
                "unit": unit_str
            },
            "detector_settings": {
                "mode": mode,
                "roi_start": roi_start,
                "roi_end": roi_end
            },
            "calibration_coefficients": {
                "c0": c0,
                "c1": c1,
                "c2": c2
            }
        }
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            QMessageBox.information(self, "Success", f"Configuration data saved successfully to:\n{file_path}")
            
            main_window.apply_calibration(self.calib_coeffs, os.path.basename(file_path))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")