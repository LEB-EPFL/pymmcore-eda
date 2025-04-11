# the calibration values for the galvanometric mirrors
# Voltage_x = position_x * m_x + a_x
# Voltage_y = position_y * m_y + a_y
# where: 
# position is measured in µm
# Voltage in mV

# Note: swap x and y from Kasia's calibration
# GALVO_CALIBRATION = {"m_x": -31.5, "m_y": 33.7, "a_x": 3137, "a_y": 708} #before 2025/04/02
GALVO_CALIBRATION = {"m_y":34.266, "m_x":  -31.73, "a_y":  -248, "a_x": 3155.99} # 2025/04/02

GALVO_MAXV = 5 #[V]
GALVO_MINV = 0 #[V]

# The maximum rate [Hz] at which the volta stream is sent to the galvo mirrors
MAX_RATE = 10e6 #[Hz]