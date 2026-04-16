from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox,
                             QLabel, QDoubleSpinBox, QAbstractSpinBox, QWidget,
                             QRadioButton, QHBoxLayout, QGroupBox)
from PyQt6.QtCore import Qt
from pressureCalc import PressureCalculator

class CustomDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

class PressureCalculatorWindow(QDialog):
    def __init__(self, parent=None, mode="nm"):
        super().__init__(parent)
        self.unit = mode
        self.setWindowTitle("Pressure Calculator")
        self.resize(450, 700)
        
        self.current_peak_val = 0.0
        self.current_peak_err = 0.0
        
        self.init_ui()
        self.setup_connections()
        self.update_mode(self.unit)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. 基本設定 (Sensor / Pressure Scale)
        top_group = QGroupBox("Base Settings")
        form = QFormLayout()
        self.combo_sensor = QComboBox()
        self.combo_p_scale = QComboBox()
        form.addRow("Sensor:", self.combo_sensor)
        form.addRow("Pressure Scale:", self.combo_p_scale)
        
        self.lbl_cur_peak = QLabel(f"0.000 {self.unit}")
        form.addRow(f"Current peak ({self.unit}):", self.lbl_cur_peak)
        
        self.spin_lam0 = CustomDoubleSpinBox()
        self.spin_lam0.setRange(-99999, 99999); self.spin_lam0.setDecimals(3)
        self.lbl_lam0_tag = QLabel(f"Zero-pressure peak ({self.unit}):")
        form.addRow(self.lbl_lam0_tag, self.spin_lam0)
        top_group.setLayout(form)
        layout.addWidget(top_group)

        # 2. 温度補正グループ
        self.temp_group = QGroupBox("Temperature Correction")
        temp_v_layout = QVBoxLayout()
        
        # On/Off ラジオボタン
        self.radio_widget = QWidget()
        radio_h = QHBoxLayout(self.radio_widget)
        self.radio_off = QRadioButton("Off"); self.radio_on = QRadioButton("On")
        self.radio_off.setChecked(True)
        radio_h.addWidget(self.radio_off); radio_h.addWidget(self.radio_on)
        temp_v_layout.addWidget(self.radio_widget)

        # 補正詳細フォーム (このウィジェットごと有効/無効を切り替える)
        self.t_form_widget = QWidget()
        self.t_form = QFormLayout(self.t_form_widget)
        
        # Temperature Scale
        self.combo_t_scale = QComboBox()
        self.lbl_t_scale_tag = QLabel("Temperature Scale:")
        self.t_form.addRow(self.lbl_t_scale_tag, self.combo_t_scale)
        
        self.spin_lam0_t0 = CustomDoubleSpinBox()
        self.spin_lam0_t0.setRange(-99999, 99999); self.spin_lam0_t0.setDecimals(3)
        self.lbl_lam0_t0_tag = QLabel(f"Zero-pressure peak at T0 ({self.unit}):")
        self.t_form.addRow(self.lbl_lam0_t0_tag, self.spin_lam0_t0)
        
        self.spin_t = CustomDoubleSpinBox(); self.spin_t.setRange(0, 5000); self.spin_t.setValue(298.15)
        self.spin_t0 = CustomDoubleSpinBox(); self.spin_t0.setRange(0, 5000); self.spin_t0.setValue(298.15)
        
        self.lbl_t_warning = QLabel("")
        self.lbl_t_warning.setStyleSheet("color: red; font-weight: bold;")
        
        self.t_form.addRow("Current T (K):", self.spin_t)
        self.t_form.addRow("", self.lbl_t_warning)
        self.t_form.addRow("Reference T0 (K):", self.spin_t0)
        
        temp_v_layout.addWidget(self.t_form_widget)
        self.temp_group.setLayout(temp_v_layout)
        layout.addWidget(self.temp_group)

        # 3. 結果表示
        self.lbl_result = QLabel("P = 0.000 +- 0.000 GPa")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setStyleSheet("background: #333; color: white; font-size: 24px; padding: 15px; border-radius: 5px;")
        layout.addWidget(self.lbl_result)

    def setup_connections(self):
        self.combo_sensor.currentTextChanged.connect(self.on_sensor_changed)
        self.combo_p_scale.currentTextChanged.connect(self.on_p_scale_changed)
        self.combo_t_scale.currentTextChanged.connect(self.calculate)
        self.spin_lam0.valueChanged.connect(self.calculate)
        self.spin_lam0_t0.valueChanged.connect(self.calculate)
        self.spin_t.valueChanged.connect(self.calculate)
        self.spin_t0.valueChanged.connect(self.calculate)
        self.radio_on.toggled.connect(self.toggle_temp_ui)

    def toggle_temp_ui(self):
        is_on = self.radio_on.isChecked()
        self.t_form_widget.setEnabled(is_on)
        self.spin_lam0.setEnabled(not is_on)
        self.calculate()

    def calculate(self):
        sensor = self.combo_sensor.currentText()
        p_scale = self.combo_p_scale.currentText()
        t_scale = self.combo_t_scale.currentText()
        curr_t = self.spin_t.value()
        
        # ★ 修正: 判定関数に p_scale ではなく sensor を渡す
        is_valid, rng = PressureCalculator.is_temp_in_range(sensor, t_scale, curr_t)
        
        if self.radio_on.isChecked() and not is_valid and rng[0] is not None:
            self.lbl_t_warning.setText(f"Warning: T out of range ({rng[0]} - {rng[1]} K)")
            self.spin_t.setStyleSheet("background-color: #FFCCCC; color: red;")
        else:
            self.lbl_t_warning.setText("")
            self.spin_t.setStyleSheet("")

        if self.current_peak_val == 0: return
        
        lam0 = self.spin_lam0.value()
        if self.radio_on.isChecked():
            lam0 = PressureCalculator.get_corrected_lam0(
                sensor, t_scale, curr_t, self.spin_t0.value(), self.spin_lam0_t0.value()
            )

        p, dp = PressureCalculator.calculate(
            sensor, p_scale, self.current_peak_val, lam0, self.current_peak_err,
            current_t=curr_t, t0=self.spin_t0.value()
        )
        
        if p is not None:
            self.lbl_result.setText(f"P = {p:.3f} +- {dp:.3f} GPa")
        else:
            self.lbl_result.setText("Calc Error")

    def update_mode(self, mode):
        self.unit = mode
        self.lbl_lam0_tag.setText(f"Zero-pressure peak ({mode}):")
        self.lbl_lam0_t0_tag.setText(f"Zero-pressure peak at T0 ({mode}):")
        
        self.combo_sensor.blockSignals(True); self.combo_sensor.clear()
        if mode == "nm":
            self.combo_sensor.addItems(["Ruby", "Sm2+:SrB4O7"])
        else:
            self.combo_sensor.addItems(["13C diamond 1st order", "Cubic BN", "Zircon v3(SiO4)"])
        self.combo_sensor.blockSignals(False)
        self.on_sensor_changed()

    def on_sensor_changed(self):
        sensor = self.combo_sensor.currentText()
        default_val = PressureCalculator.INITIAL_VALUES.get(sensor, 0.0)
        self.spin_lam0.setValue(default_val)
        self.spin_lam0_t0.setValue(default_val)
        
        self.combo_p_scale.blockSignals(True); self.combo_p_scale.clear()
        self.combo_t_scale.blockSignals(True); self.combo_t_scale.clear()
        
        # PDFの仕様に合わせたセンサーごとの選択肢
        if sensor == "Ruby":
            self.combo_p_scale.addItems(["Shen et al. 2020", "Mao et al. 1986", "Piermarini et al. 1975"])
            self.combo_t_scale.addItems(["Ragan et al. 1992"])
        elif sensor == "Sm2+:SrB4O7":
            self.combo_p_scale.addItems(["Datchi 1997", "Leger 1990", "Rashchenko 2015"])
            self.combo_t_scale.addItems(["Datchi et al. 2007"])
        elif sensor == "13C diamond 1st order":
            self.combo_p_scale.addItems(["Schiferl et al. 1997"])
            self.combo_t_scale.addItems(["Schiferl et al. 1997"])
        elif sensor == "Cubic BN":
            self.combo_p_scale.addItems(["Datchi et al. 2004"])
        elif sensor == "Zircon v3(SiO4)":
            self.combo_p_scale.addItems(["Schmidt et al. 2013"])
        
        self.combo_p_scale.blockSignals(False); self.combo_t_scale.blockSignals(False)
        self.on_p_scale_changed()

    def on_p_scale_changed(self):
        scale = self.combo_p_scale.currentText()
        is_pt_scale = (scale == "Schiferl et al. 1997")
        self.radio_widget.setVisible(not is_pt_scale)
        self.lbl_t_scale_tag.setVisible(not is_pt_scale)
        self.combo_t_scale.setVisible(not is_pt_scale)
        if is_pt_scale: self.radio_on.setChecked(True)
        self.toggle_temp_ui()

    def set_current_peak(self, val, err=0.0):
        self.current_peak_val, self.current_peak_err = val, err
        self.lbl_cur_peak.setText(f"{val:.3f} {self.unit}")
        self.calculate()