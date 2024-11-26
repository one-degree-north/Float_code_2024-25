#potential errors in code:
#ardruino isnt coded to do anything when 'in' command is sent
#gui never sends 'plot' command to ardruino
#ardruino isnt coded to do anything when 'mount' command is sent
#when ardruino recieves 'float' command, it mounts

import sys#system operator
from PyQt6.QtWidgets import (QWidget, QLabel, QApplication, QMainWindow, #gui stuff
                           QHBoxLayout, QPushButton, QVBoxLayout, QFrame)
from PyQt6.QtGui import QIcon, QPalette, QColor, QPen, QPainter, QFont#gui stuff
from PyQt6.QtCore import Qt, QTimer#gui stuff
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg#graph
from matplotlib.figure import Figure#graph
import socket
import select#module for wifi
import re
#importing all modules

class ModernFloatWindow(QMainWindow):#main class for the gui
    def __init__(self):#main method for a class
        super().__init__()#gets all the methods and stuff from the QMainWindow class(child class)
        self.xAxis = []#x axis list for graph
        self.yAxis = []#y axis list for graph
        self.floatCount = 0#float count
        self.inCount = 0#counts its in
        self.espIPAddress = '192.168.10.102'#ip address to connect with ardruino wifi controller
        self.espPort = 80#port to connect with ardruino wifi controller
        
        # Store labels as instance variables for updating
        self.company_label = None#gui stuff
        self.depth_label = None#gui stuff
        self.pressure_label = None#gui stuff
        self.time_label = None#gui stuff
        
        # Set dark theme colors
        self.colors = {
            'background': '#1a1a1a',
            'card': '#2d2d2d',
            'accent': '#007AFF',
            'text': '#ffffff',
            'text_secondary': '#909090'
        }
        
        # Initialize control buttons as instance variables
        self.float_down = None#button for float down
        self.plot_button = None#button for graph plot
        self.in_button = None#button for float in
        self.mount_button = None#button for float mount
        
        self.setupGUI()#calls setupgui method
        self.connectSignals()#calls the connect signals method

    def connectSignals(self):
        self.float_down.clicked.connect(self.onFloatDownClicked)#connects float down button to the method in brackets
        self.plot_button.clicked.connect(self.sendPlotCommand)#connects graph plot button to the method in brackets
        self.in_button.clicked.connect(self.sendInCommand)#connects float in button to the method in brackets
        self.mount_button.clicked.connect(self.sendMountCommand)#connects float mount button to the method in brackets

    def setupGUI(self):
        self.setWindowTitle("Float Control System")#window title 
        self.resize(1400, 800)#Resizes the window
        self.setStyleSheet(f"background-color: {self.colors['background']};")#background color of window

        main_widget = QWidget()#creates a window widget
        main_layout = QHBoxLayout()#creates a box layout (horizontal)
        
        left_panel = self.createLeftPanel()#calls the method to create left panel of the screen
        center_panel = self.createCenterPanel()#calls the method to create middle panel of the screen
        right_panel = self.createRightPanel()#calls the method to create the right panel of the screen

        main_layout.addWidget(left_panel, 1)#adds the widget to the main layout
        main_layout.addWidget(center_panel, 2)#adds the widget to the main layout
        main_layout.addWidget(right_panel, 1)#adds the widget to the main layout
        
        main_widget.setLayout(main_layout)#Sets the main layout to the main_layout
        self.setCentralWidget(main_widget)#sets the central/main widget to main_widget

    def createLeftPanel(self):#
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
        self.company_label = self.createStatusCard("Company Number", "RN16")
        self.depth_label = self.createStatusCard("Current Depth", "0.00 m")
        self.pressure_label = self.createStatusCard("Pressure", "101.3 kPa")
        self.time_label = self.createStatusCard("Time", "00:00:00")

        layout.addWidget(self.company_label)
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

    def updateStatusLabels(self, company_number=None, depth=None, pressure=None, time=None):
        if company_number is not None:
            self.company_label.value_label.setText(str(company_number))
        if depth is not None:
            self.depth_label.value_label.setText(f"{depth:.2f} m")
        if pressure is not None:
            self.pressure_label.value_label.setText(f"{pressure:.1f} kPa")
        if time is not None:
            self.time_label.value_label.setText(str(time))

    def updateGraph(self, times, depths):#method to update graph using times and depth array
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

    def processReceivedData(self, data):#method to process the received data
        try:#tries to carry out these operations, if an error occurs it goes below
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
                    if len(details) == 3:  # Ensure we have time, depth, pressure
                        if float(details[1]) > -1 and len(details[1]) > 0 and len(details[2]) > 0:
                            times.append(details[0])#adds times to time array
                            depths.append(float(details[1]) + 0.3)  # Adjusted depth, added to depth array
                            pressures.append(float(details[2]))#pressure added to pressure array
                            
                            # Update latest values in status
                            self.updateStatusLabels(
                                depth=float(details[1]) + 0.3,
                                pressure=float(details[2]),
                                time=details[0]
                            )

                # Update the graph with collected data
                self.updateGraph(times, depths)

        except Exception as e:#if there is an error in the above code, it jumps down here and returns error
            print(f"Error processing received data: {e}")

    def onFloatDownClicked(self):#whenever float down button is clicked, its linked here
        self.floatCount += 1#counts how many times float down is clicked
        self.sendFloatCommand()#calls the sendFloatCommand method
        
    def sendFloatCommand(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.espIPAddress, self.espPort))#connects to ardruino wifi with ip address and port
                s.setblocking(0)#makes sure socket doesn't freeze while trying to connect
                s.sendall(b'float')#sends the command 'float' for the ardruino
                print("attempting")

                while True:
                    ready = select.select([s], [], [], 1)#waits for 1 second for socket to become available for reading data
                    if ready[0]:#checks if there is data or not
                        data = s.recv(1024)#reads 1024 bits of data 
                        if not data:#if no data, then skips while loop execution
                            break

                        detailed_response = data.decode('utf-8').strip()#decodes the data using utf-8
                        print("Received:", detailed_response)

                        if detailed_response.startswith("Company Number"):#if the data starts with "company number", 
                            self.processReceivedData(detailed_response)#it goes to another method with the decoded message as param
                            break

        except Exception as e:
            print(f"Failed to send float command: {e}")

    def sendPlotCommand(self):
        # For testing, using sample data until real data is used
        times = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
        depths = [-4, -4, -4, -58, -101, -178, -258, -325, -382, -388, -396, -396, -396, -374, -321, -234, -145, -92, -32, -4, -4]
        self.updateGraph(times, depths)

    def sendInCommand(self):#method when 'in' button is clicked
        if self.inCount == 0:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.espIPAddress, self.espPort))#connects to ardruino wifi with that ip and port
                    s.setblocking(0)#makes sure socket doesnt freeze while sending
                    s.sendall(b'in')#tells the float that the command is 'in'
                    print("pushing in")
                    self.inCount += 1
            except Exception as e:#any error, it comes here
                print(f"Failed to send command: {e}")
        else:
            print("Already Pushed")

    def sendMountCommand(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.espIPAddress, self.espPort))#connects to ardruino wifi with that ip and port
                s.setblocking(0)#makes sure socket doesn't freeze while seending
                s.sendall(b'mount')#sends the command 'mount' to let the float know it needs to mount
                print("Mount command sent")
        except Exception as e:#any error, it comes here
            print(f"Failed to send mount command: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernFloatWindow()
    window.show()
    sys.exit(app.exec())

    
