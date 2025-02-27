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
        self.project_label = None
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

    def connectSignals(self):
        self.float_down.clicked.connect(self.onFloatDownClicked)
        self.plot_button.clicked.connect(self.sendPlotCommand)
        self.in_button.clicked.connect(self.sendInCommand)
        self.mount_button.clicked.connect(self.sendMountCommand)

    def setupGUI(self):
        self.setWindowTitle("Float Control System")
        self.resize(1400, 800)
        self.setStyleSheet(f"background-color: {self.colors['background']};")

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        left_panel = self.createLeftPanel()
        center_panel = self.createCenterPanel()
        right_panel = self.createRightPanel()

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(center_panel, 2)
        main_layout.addWidget(right_panel, 1)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def createLeftPanel(self):
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 15px;
                margin: 10px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create and store labels for updating
        self.project_label = self.createStatusCard("MATE", "Float")
        self.depth_label = self.createStatusCard("Current Depth", "0.00 m")
        self.pressure_label = self.createStatusCard("Pressure", "101.3 kPa")
        self.time_label = self.createStatusCard("Time", "00:00:00")

        layout.addWidget(self.project_label)
        layout.addWidget(self.depth_label)
        layout.addWidget(self.pressure_label)
        layout.addWidget(self.time_label)

        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def createStatusCard(self, title, value):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['background']};
                border-radius: 10px;
                padding: 5px;
                margin: 2px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 18px;
            font-weight: bold;
        """)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            color: {self.colors['text']};
            font-size: 24px;
            font-weight: bold;
        """)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.setLayout(layout)
        
        # Store the value label in the card for updating
        card.value_label = value_label
        return card

    def createCenterPanel(self):
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 15px;
                margin: 10px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Depth Profile")
        title.setStyleSheet(f"""
            color: {self.colors['text']};
            font-size: 24px;
            font-weight: bold;
            padding: 0px;
            margin: 0px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)

        self.figure = Figure(facecolor=self.colors['card'])
        self.figure.subplots_adjust(top=0.95, bottom=0.1, left=0.1, right=0.95)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_facecolor(self.colors['card'])
        
        self.axes.tick_params(colors=self.colors['text'])
        for spine in self.axes.spines.values():
            spine.set_color(self.colors['text_secondary'])
        
        self.axes.set_xlabel('Time (s)', color=self.colors['text'])
        self.axes.set_ylabel('Depth (m)', color=self.colors['text'])
        
        layout.addWidget(self.canvas)
        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def createRightPanel(self):
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 15px;
                margin: 10px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.float_down = self.createStyledButton("FLOAT DOWN")
        self.plot_button = self.createStyledButton("PLOT DATA")
        self.in_button = self.createStyledButton("IN")
        self.mount_button = self.createStyledButton("MOUNT")

        layout.addWidget(self.float_down)
        layout.addWidget(self.plot_button)
        layout.addWidget(self.in_button)
        layout.addWidget(self.mount_button)
        layout.addStretch(1)

        panel.setLayout(layout)
        return panel

    def createStyledButton(self, text):
        button = QPushButton(text)
        button.setFixedSize(200, 60)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent']};
                color: white;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: #0056b3;
            }}
            QPushButton:pressed {{
                background-color: #003d80;
            }}
        """)
        return button

    def onFloatDownClicked(self):
        self.floatCount += 1
        self.sendFloatCommand()

    def sendInCommand(self):
        print("'In' command not implemented in Arduino")
        if self.inCount == 0:
            self.inCount += 1

    def sendMountCommand(self):
        print("'Mount' command not implemented in Arduino")

    def processReceivedData(self, data):
        try:
            # Check if data contains the project number separator
            if '|' in data:
                # Original format with project number
                parts = data.split('|')
                project_number = parts[0]  # project number is the first part
                
                # Update project number in status
                self.updateStatusLabels(project_number=project_number)
                
                # Data points are in the second part
                if len(parts) > 1:
                    data_points_str = parts[1]
                else:
                    data_points_str = ""
            else:
                # New format without project number - directly from Arduino
                data_points_str = data
                # Keep project number as is
    
            # Process the data points if any exist
            if data_points_str:
                data_points = data_points_str.split(';')
                times = []
                depths = []
                pressures = []
    
                for point in data_points:
                    if not point:  # Skip empty points
                        continue
                        
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
            print(f"Data was: {data}")

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
    
                        # Process any response from Arduino, regardless of format
                        self.processReceivedData(detailed_response)
                        break
    
        except Exception as e:
            print(f"Failed to send float command: {e}")

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
                        
                        # Process any response from Arduino, regardless of format
                        self.processReceivedData(detailed_response)
                        break
    
        except Exception as e:
            print(f"Failed to send plot command: {e}")

    def updateStatusLabels(self, project_number=None, depth=None, pressure=None, time=None):
        if project_number is not None:
            self.project_label.value_label.setText(str(project_number))
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernFloatWindow()
    window.show()
    sys.exit(app.exec())
