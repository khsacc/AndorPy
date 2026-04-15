# Andor Spectrometer Control & Analysis GUI

Andor製のカメラ（検出器）および分光器を制御し、スペクトルのリアルタイム取得からバックグラウンド補正、キャリブレーション、ピークフィッティング、そして高圧実験における圧力計算までを一貫して行うためのPythonベースのGUIアプリケーションです。

## ✨ 主な機能 (Features)

* **リアルタイム測定・制御**
  * 1Dスペクトル（Full Range / Custom ROI）および2Dイメージのリアルタイム表示
  * 露光時間、アキュムレーション（積算）回数、検出器冷却温度の制御
  * シングル測定、連続測定、および一定間隔での自動保存（Sequential measurements）
* **分光器制御**
  * 回折格子（Grating）および中心波長の制御
  * 波長（nm）とラマンシフト（cm⁻¹）モードのシームレスな切り替え機能（励起波長設定対応）
* **バックグラウンド補正・キャリブレーション**
  * バックグラウンドスペクトルの取得、保存、リアルタイム差し引き
  * X軸の波長キャリブレーション機能（過去のキャリブレーションファイルの読み込み対応）
* **リアルタイム・ピークフィッティング**
  * Gauss, Lorentz, Pseudo Voigt 関数の単一ピーク・ダブルピークフィッティング
  * フィッティング範囲の自動・手動設定
* **圧力計算機能 (高圧実験向け)**
  * ルビー蛍光法を用いた圧力計算（Piermarini, Mao, Shenスケール等に対応）
  * サンプル温度を考慮した中心波長（λ0）の温度補正機能

## 🛠 必須環境 (Requirements)

* **OS**: Windows 10 / 11 (Andor SDKの動作環境に依存します)
* **Python**: Python 3.8 以上
* **Hardware**:
  * Andor製 カメラ（検出器）
  * Andor製 分光器
* **Drivers/SDK**:
  * Andor SDK (ドライバパッケージがPCにインストールされている必要があります)

### 依存Pythonパッケージ
* PyQt6
* pyqtgraph
* numpy
* scipy

## 📥 インストール方法 (Installation)

1. コマンドプロンプトまたはPowerShellを開きます。
2. 必要なPythonパッケージをインストールします。

    pip install PyQt6 pyqtgraph numpy scipy

3. Andor SDKが正しくインストールされていることを確認します。
4. このプロジェクトのディレクトリに移動し、スクリプトを実行します。

## 🚀 使い方 (Usage)

### 起動方法
以下のコマンドでアプリケーションを起動します。

    python ui.py

※ ハードウェアを接続せずにUIのテストだけを行いたい場合は、デバッグモードで起動できます。

    python ui.py --debug

### 基本的な測定フロー
1. **冷却の開始**:
   右側パネル「Measurement」内の「Cooler target temp」を設定し、カメラの冷却が安定するのを待ちます。
2. **分光器の設定**:
   「Spectrometer Configurations」セクションで、使用する回折格子と中心波長（またはラマンシフト）を入力し、**「Apply」** をクリックして分光器を動かします。
3. **バックグラウンドの取得 (任意)**:
   シャッターを閉じた状態で「Background」セクションの **「Acquire and save background」** をクリックし、バックグラウンドデータを取得・保存します。
4. **測定の実行**:
   * **Take single spectrum**: 設定された露光時間と積算回数で1回だけ測定を行います。
   * **Commence Measurement**: 連続的にスペクトルを取得し、画面にリアルタイム表示します。停止するには「Terminate Measurement」を押します。
5. **データの保存**:
   * 現在表示されているスペクトルを保存するには **「Save data」** をクリックします。
   * 自動的に連続保存したい場合は、**「▶ Sequential measurements」** を開き、ディレクトリと保存間隔（Skip frames）、最大保存枚数を設定して **「Start Sequential」** をクリックします。

### フィッティングと圧力計算
* 「Fitting Configurations」を **ON** にすると、表示されているスペクトルに対してリアルタイムでフィッティングが行われます。
* ダブルピークでフィッティングが成功している場合、「Pressure Calculation」セクションを **ON** にすることで、ルビーのR1ピークから圧力を自動計算して表示させることができます。

## 📁 ファイル構成 (File Structure)

* ui.py: メインのGUIアプリケーションスクリプト。
* camera.py: Andorカメラを制御し、データや温度を取得するスレッドクラス。
* spectrometer.py: Andor分光器の回折格子や波長を制御するモジュール。
* analysis.py: スペクトルデータのピークフィッティング処理を行います。
* calibration_ui.py: ピクセルから波長へのキャリブレーションを行うためのUI。
* pressureCalc.py: ルビー蛍光から圧力を算出するモジュール。
* spectrometerConfig.json: 回折格子の設定等を保存する設定ファイル（初回起動時に生成）。