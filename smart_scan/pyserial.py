import serial
from dataclasses import dataclass


@dataclass
class Laser:
    COM_PORT: str = "COM5"
    BAUD: int = 115200
    timeout: int = 1

    def __post_init__(self):
        # Initialize the serial connection
        self.ser = serial.Serial(self.COM_PORT, self.BAUD, timeout=self.timeout)

    # Commands
    on: str = "la on\r"  # Laser on
    off: str = "la off\r"  # Laser off
    show_power: str = "sh pow\r"  # Show laser power in uW

    def set_power(self, power: int) -> str:
        """
        Returns the command to set the laser power in uW.
        """
        return f"ch 1 pow {power} mic\r"

    def send(self, cmd: str) -> None:
        """
        Send a command to the laser device and read the response.
        """
        self.ser.write(cmd.encode())
        self.ser.flush()

        response = self.ser.readline()
        print(response)
        while response:
            print(response)
            response = self.ser.readline()

    def disconnect(self):
        self.ser.flush()
        self.ser.close()

