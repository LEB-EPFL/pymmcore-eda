# the calibration values for the galvanometric mirrors
# Voltage_x = position_x * m_x + a_x
# Voltage_y = position_y * m_y + a_y
# where: 
# position is measured in µm
# Voltage in mV
GALVO_CALIBRATION = {"m_x": 30, "m_y": 30, "a_x": 500, "a_y": 500}

GALVO_CALIBRATION = {"m_x": 29.2, "m_y": 32, "a_x": 520, "a_y": 600}
GALVO_MAXV = 5 #[V]
GALVO_MINV = 0 #[V]

# The maximum rate [Hz] at which the volta stream is sent to the galvo mirrors
MAX_RATE = 1e3 #[Hz]