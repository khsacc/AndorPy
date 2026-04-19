def SpectrometerController(config=None, debug=False):
    model = config.get("model", "Andor") if config else "Andor"
    
    if model == "PrincetonInstruments":
        from src.spectrometer_princeton import SpectrometerControllerPI
        return SpectrometerControllerPI(config=config, debug=debug)
    else:
        from src.spectrometer_andor import SpectrometerControllerAndor
        return SpectrometerControllerAndor(debug=debug)

import json
try:
    with open("spectrometerConfig.json", "r") as f:
        _model = json.load(f).get("model", "Andor")
except:
    _model = "Andor"

if _model == "PrincetonInstruments":
    from src.spectrometer_princeton import SpectrometerMoveThread
else:
    from src.spectrometer_andor import SpectrometerMoveThread