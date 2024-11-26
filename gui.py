import sys
from PyQt6.QtWidgets import (QWidget, QLabel, QApplication, QMainWindow, 
                           QHBoxLayout, QPushButton, QVBoxLayout, QFrame)
from PyQt6.QtGui import QIcon, QPalette, QColor, QPen, QPainter, QFont
from PyQt6.QtCore import Qt, QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import socket
import select
import re

class ModernFloatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.xAxis = []
        self.yAxis = []
        self.floatCount = 0
        self.inCount = 0
        self.espIPAddress = '192.168.10.102'
        self.espPort = 80
        
        # Store labels as instance variables for updating
        self.company_label = None
        self.depth_label = None
        self.pressure_label = None
        self.time_label = None
        
        # Set dark theme colors
        self.colors = {
            'background': '#1a1a1a',
            'card': '#2d2d2d',
            'accent': '#007AFF',
            'text': '#ffffff',
            'text_secondary': '#909090'
        }
        
        # Initialize control buttons as instance variables
        self.float_down = None
        self.plot_button = None
        self.in_button = None
        self.mount_button = None
        
        self.setupGUI()
        self.connectSignals()

    # [Previous GUI setup methods remain the same until the command methods]

    def sendPlotCommand(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.espIPAddress, self.espPort))
                s.setblocking(0)
                s.sendall(b'plot')
                print("Requesting plot data")

                while True:
                    ready = select.select([s], [], [], 1)
                    if ready[0]:
                        data = s.recv(1024)
                        if not data:
                            break

                        detailed_response = data.decode('utf-8').strip()
                        print("Received:", detailed_response)
                        self.processReceivedData(detailed_response)
                        break

        except Exception as e:
            print(f"Failed to send plot command: {e}")

    def sendFloatCommand(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.espIPAddress, self.espPort))
                s.setblocking(0)
                s.sendall(b'float')
                print("Sending float command (includes mounting)")

                while True:
                    ready = select.select([s], [], [], 1)
                    if ready[0]:
                        data = s.recv(1024)
                        if not data:
                            break

                        detailed_response = data.decode('utf-8').strip()
                        print("Received:", detailed_response)

                        if detailed_response.startswith(("Company Number", "RN16")):
                            self.processReceivedData(detailed_response)
                            break

        except Exception as e:
            print(f"Failed to send float command: {e}")

    def sendInCommand(self):
        print("'In' command not implemented in Arduino")
        if self.inCount == 0:
            self.inCount += 1

    def sendMountCommand(self):
        print("'Mount' command not implemented in Arduino")

    def processReceivedData(self, data):
        try:
            # Splitting the data based on '|'
            parts = data.split('|')
            company_number = parts[0]  # Company number is the first part
            
            # Update company number in status
            self.updateStatusLabels(company_number=company_number)

            # Process the data points
            if len(parts) > 1:
                data_points = parts[1].split(';')
                times = []
                depths = []
                pressures = []

                for point in data_points:
                    details = point.split(':')
                    if len(details) == 3:  # time:depth:pressure format
                        time_val = details[0]
                        depth_val = float(details[1])
                        pressure_val = float(details[2])
                        
                        times.append(time_val)
                        depths.append(depth_val)
                        pressures.append(pressure_val)
                        
                        # Update latest values in status
                        self.updateStatusLabels(
                            depth=depth_val,
                            pressure=pressure_val,
                            time=f"{time_val}s"
                        )

                # Update the graph with collected data
                if times and depths:
                    self.updateGraph(times, depths)

        except Exception as e:
            print(f"Error processing received data: {e}")

    def updateStatusLabels(self, company_number=None, depth=None, pressure=None, time=None):
        if company_number is not None:
            self.company_label.value_label.setText(str(company_number))
        if depth is not None:
            self.depth_label.value_label.setText(f"{depth:.2f} m")
        if pressure is not None:
            self.pressure_label.value_label.setText(f"{pressure:.1f} kPa")
        if time is not None:
            self.time_label.value_label.setText(str(time))

    def updateGraph(self, times, depths):
        self.xAxis = [float(time) for time in times]
        self.yAxis = depths
        self.axes.clear()
        
        self.axes.set_facecolor(self.colors['card'])
        self.axes.tick_params(colors=self.colors['text'])
        for spine in self.axes.spines.values():
            spine.set_color(self.colors['text_secondary'])
        
        self.axes.plot(self.xAxis, self.yAxis, 
                      color=self.colors['accent'],
                      linewidth=2,
                      label='Depth (meters)')
        
        self.axes.set_xlabel('Time (s)', color=self.colors['text'])
        self.axes.set_ylabel('Depth (m)', color=self.colors['text'])
        self.axes.legend(facecolor=self.colors['card'], 
                        labelcolor=self.colors['text'])
        
        self.canvas.draw()

    # [All the GUI creation methods (createLeftPanel, createCenterPanel, etc.) remain exactly the same]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernFloatWindow()
    window.show()
    sys.exit(app.exec())
