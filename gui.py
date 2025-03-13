import sys
from PyQt6.QtWidgets import (QWidget, QLabel, QApplication, QMainWindow, 
                           QHBoxLayout, QPushButton, QVBoxLayout, QFrame,
                           QLineEdit, QMessageBox)
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
        
        # Default IP address - can be changed by user
        self.espIPAddress = '192.168.10.102'
        self.espPort = 80
        
        # Store labels as instance variables for updating
        self.project_label = None
        self.depth_label = None
        self.pressure_label = None
        self.time_label = None
        self.connection_status = None
        
        # Command status tracking
        self.is_float_mounted = False
        
        # Set dark theme colors
        self.colors = {
            'background': '#1a1a1a',
            'card': '#2d2d2d',
            'accent': '#007AFF',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'text': '#ffffff',
            'text_secondary': '#909090'
        }
        
        # Initialize control buttons as instance variables
        self.float_down = None
        self.plot_button = None
        self.in_button = None
        self.mount_button = None
        self.ip_input = None
        
        # Setup timer for periodic status updates
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.updateConnectionStatus)
        
        self.setupGUI()
        self.connectSignals()
        
        # Start the timer
        self.status_timer.start(5000)  # Check connection every 5 seconds

    def connectSignals(self):
        self.float_down.clicked.connect(self.onFloatDownClicked)
        self.plot_button.clicked.connect(self.sendPlotCommand)
        self.in_button.clicked.connect(self.sendInCommand)
        self.mount_button.clicked.connect(self.sendMountCommand)
        self.ip_input.returnPressed.connect(self.updateIPAddress)

    def setupGUI(self):
        self.setWindowTitle("MATE Float Control System")
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
        
        # Add connection status
        self.connection_status = self.createStatusCard("Connection", "Checking...")

        layout.addWidget(self.project_label)
        layout.addWidget(self.depth_label)
        layout.addWidget(self.pressure_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.connection_status)
        
        # Add IP address input
        ip_layout = QHBoxLayout()
        ip_label = QLabel("Float IP:")
        ip_label.setStyleSheet(f"color: {self.colors['text']};")
        self.ip_input = QLineEdit(self.espIPAddress)
        self.ip_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['background']};
                color: {self.colors['text']};
                border-radius: 5px;
                padding: 5px;
            }}
        """)
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        layout.addLayout(ip_layout)

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
        
        # Invert y-axis for more intuitive depth display (0 at surface, increasing as you go deeper)
        self.axes.invert_yaxis()
        
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

        self.mount_button = self.createStyledButton("MOUNT")
        self.float_down = self.createStyledButton("FLOAT DOWN")
        self.plot_button = self.createStyledButton("PLOT DATA")
        self.in_button = self.createStyledButton("RETURN FLOAT")

        layout.addWidget(self.mount_button)
        layout.addWidget(self.float_down)
        layout.addWidget(self.plot_button)
        layout.addWidget(self.in_button)
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

    def updateIPAddress(self):
        new_ip = self.ip_input.text().strip()
        if new_ip:
            self.espIPAddress = new_ip
            self.updateConnectionStatus()
            self.showMessage("IP Address Updated", f"Float IP set to: {new_ip}")

    def updateConnectionStatus(self):
        # Try to connect to the ESP8266 to check status
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)  # Short timeout for quick check
                s.connect((self.espIPAddress, self.espPort))
                self.connection_status.value_label.setText("Connected")
                self.connection_status.value_label.setStyleSheet(f"color: {self.colors['success']}; font-size: 24px; font-weight: bold;")
        except Exception:
            self.connection_status.value_label.setText("Disconnected")
            self.connection_status.value_label.setStyleSheet(f"color: {self.colors['danger']}; font-size: 24px; font-weight: bold;")

    def onFloatDownClicked(self):
        if not self.is_float_mounted:
            self.showMessage("Error", "Float must be mounted first. Please click MOUNT button.")
            return
            
        self.floatCount += 1
        self.sendFloatCommand()

    def sendInCommand(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3.0)
                s.connect((self.espIPAddress, self.espPort))
                s.sendall(b'in')
                print("Sending 'in' command")
                
                try:
                    data = s.recv(1024)
                    response = data.decode('utf-8').strip()
                    print("Received:", response)
                    self.is_float_mounted = False
                    self.showMessage("Success", "Float returned to surface")
                except socket.timeout:
                    self.showMessage("Warning", "No response from float, but command was sent")
        except Exception as e:
            self.showMessage("Error", f"Failed to send command: {str(e)}")

    def sendMountCommand(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3.0)
                s.connect((self.espIPAddress, self.espPort))
                s.sendall(b'mount')
                print("Sending 'mount' command")
                
                try:
                    data = s.recv(1024)
                    response = data.decode('utf-8').strip()
                    print("Received:", response)
                    self.is_float_mounted = True
                    self.showMessage("Success", "Float mounted successfully")
                except socket.timeout:
                    self.is_float_mounted = True
                    self.showMessage("Warning", "No response from float, but command was sent")
        except Exception as e:
            self.showMessage("Error", f"Failed to send command: {str(e)}")

    def processReceivedData(self, data):
        try:
            # First check if this is a simple status message
            if ',' in data and not ';' in data:
                # Simple status message format: "Time: 0, Pressure: 101.3, Depth: 0.05"
                matches = re.findall(r'Time: (\d+), Pressure: ([0-9.]+), Depth: ([0-9.]+)', data)
                if matches and len(matches[0]) == 3:
                    time_val = matches[0][0]
                    pressure_val = float(matches[0][1])
                    depth_val = float(matches[0][2])
                    
                    self.updateStatusLabels(
                        depth=depth_val,
                        pressure=pressure_val,
                        time=f"{time_val}s"
                    )
                return
                
            # Process data points in time:depth:pressure format
            if ';' in data or ':' in data:  # Multiple data points or at least one data point
                data_points = data.split(';')
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
                        
                # Update latest values in status if we have data
                if times and depths:
                    self.updateStatusLabels(
                        depth=depths[-1],
                        pressure=pressures[-1],
                        time=f"{times[-1]}s"
                    )
                    
                    # Update the graph with collected data
                    self.updateGraph(times, depths)
    
        except Exception as e:
            print(f"Error processing received data: {e}")
            print(f"Data was: {data}")

    def sendFloatCommand(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)  # Increase timeout for float operation
                s.connect((self.espIPAddress, self.espPort))
                s.sendall(b'float')
                print("Sending float command")
                
                try:
                    data = s.recv(1024)
                    detailed_response = data.decode('utf-8').strip()
                    print("Received:", detailed_response)
                    
                    # Process initial status from Arduino
                    self.processReceivedData(detailed_response)
                    self.showMessage("Info", "Float operation started. Retrieving data...")
                    
                    # After float operation completes, get the data
                    self.sendPlotCommand()
                except socket.timeout:
                    self.showMessage("Warning", "Float operation started but no response received")
                    
                    # Try to get data anyway
                    self.sendPlotCommand()
    
        except Exception as e:
            self.showMessage("Error", f"Failed to send float command: {str(e)}")

    def sendPlotCommand(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((self.espIPAddress, self.espPort))
                s.sendall(b'plot')
                print("Requesting plot data")
    
                try:
                    data = s.recv(1024)
                    detailed_response = data.decode('utf-8').strip()
                    print("Received data:", detailed_response)
                    
                    if not detailed_response:
                        self.showMessage("Info", "No data points available yet")
                    else:
                        # Process any response from Arduino
                        self.processReceivedData(detailed_response)
                        self.showMessage("Success", "Data retrieved and plotted successfully")
                except socket.timeout:
                    self.showMessage("Warning", "Timeout while waiting for plot data")
    
        except Exception as e:
            self.showMessage("Error", f"Failed to send plot command: {str(e)}")

    def updateStatusLabels(self, depth=None, pressure=None, time=None):
        if depth is not None:
            self.depth_label.value_label.setText(f"{depth:.2f} m")
        if pressure is not None:
            self.pressure_label.value_label.setText(f"{pressure:.1f} kPa")
        if time is not None:
            self.time_label.value_label.setText(str(time))

    def updateGraph(self, times, depths):
        try:
            self.xAxis = [float(time) for time in times]
            self.yAxis = [float(depth) for depth in depths]
            
            self.axes.clear()
            
            self.axes.set_facecolor(self.colors['card'])
            self.axes.tick_params(colors=self.colors['text'])
            for spine in self.axes.spines.values():
                spine.set_color(self.colors['text_secondary'])
            
            self.axes.plot(self.xAxis, self.yAxis, 
                          color=self.colors['accent'],
                          linewidth=2,
                          marker='o',
                          label='Depth (meters)')
            
            # Add horizontal line at competition target depth (2.5m)
            self.axes.axhline(y=2.5, color=self.colors['success'], linestyle='--', alpha=0.7)
            
            # Add shaded area for valid depth range (2.0-3.0m, ±50cm from target)
            self.axes.axhspan(2.0, 3.0, alpha=0.2, color=self.colors['success'])
            
            self.axes.set_xlabel('Time (s)', color=self.colors['text'])
            self.axes.set_ylabel('Depth (m)', color=self.colors['text'])
            
            # Invert y-axis to show depth correctly (0 at top, increasing downward)
            self.axes.invert_yaxis()
            
            self.axes.legend(facecolor=self.colors['card'], 
                            labelcolor=self.colors['text'])
            
            self.canvas.draw()
        except Exception as e:
            print(f"Error updating graph: {e}")

    def showMessage(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Style the message box
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.colors['card']};
                color: {self.colors['text']};
            }}
            QPushButton {{
                background-color: {self.colors['accent']};
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                font-weight: bold;
            }}
        """)
        
        msg_box.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernFloatWindow()
    window.show()
    sys.exit(app.exec())
