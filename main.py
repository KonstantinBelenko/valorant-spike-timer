import sys
import threading
from pynput import mouse
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer, QEvent, QObject
from PyQt5.QtGui import QPainter, QColor

import numpy as np
import pyautogui as pag
import cv2

class Detector:
    
    def __init__(self, on_detect_callback = None) -> None:
        if on_detect_callback is None:
            on_detect_callback = lambda: None

        self.on_detect_callback = on_detect_callback
        
    def _screenshot(self) -> np.ndarray:
        screen_width, screen_height = pag.size()
        
        # Define the width and height of the region to capture
        region_width, region_height = 75, 75

        # Calculate the left and top coordinates to center the region at the top of the screen
        # Adjust the left coordinate slightly to fine-tune the centering
        left = (screen_width - region_width) // 2# Adjusting by 10 pixels for fine-tuning
        top = 10

        region = (left, top, region_width, region_height)

        return np.array(pag.screenshot(region=region))

        
    def detect(self, img: str = None) -> bool:
        if img is None:
            img = self._screenshot()
        else:
            img = cv2.imread(img)
            
        v_min = np.array([124, 0, 0])
        v_max = np.array([170, 0, 0])

        # Check if the image primarily contains the color in range
        mask = cv2.inRange(img, v_min, v_max)
        num_pixels = np.sum(mask == 255)
        print(num_pixels)
        if num_pixels > 100:
            self.on_detect_callback()
            return True
        else:
            return False
        

class Overlay(QWidget):
    def __init__(self, button_tracker):
        super().__init__()
        self.button_tracker = button_tracker  # Store 
        self.timer_active = True
        self.initUI()

    def initUI(self):
        self.setup_timer_label()
        self.setup_timer()
        self.setup_window_properties()

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.start_timer()

    def setup_timer_label(self):
        self.timer_label = QLabel(self)
        self.timer_label.move(50, 50)
        self.timer_label.setStyleSheet("font-size: 24px; color: red")

    def setup_window_properties(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, 200, 100)

    def configure_ui(self, time_left):
        self.timer_label.setText(str(time_left))
        self.update()

    def paintEvent(self, event):
        if hasattr(self, "seconds_left"):
            painter = QPainter(self)

            # Draw outside rect (white, slightly bigger than inside rect)
            painter.setPen(Qt.white)
            painter.setBrush(Qt.white)
            painter.drawRect(5, 70, 190, 20)

            # Calculate the widths of the green and blue sections
            # Calculate the widths of the green and blue sections
            total_width = 180
            blue_width = int((7 / 45) * total_width)
            green_width = int((self.seconds_left / 45) * total_width) - blue_width

            # Draw inside rect (blue section)
            painter.setBrush(QColor(0, 0, 255))

            if self.seconds_left > 7:
                painter.drawRect(10, 75, blue_width, 10)
                
                # Draw inside rect (green section)
                painter.setBrush(QColor(0, 255, 0))
                painter.drawRect(10 + blue_width, 75, green_width, 10)
            else:
                blue_drain_width = int((self.seconds_left / 7) * blue_width)
                painter.drawRect(10, 75, blue_drain_width, 10)
            painter.end()

    def start_timer(self):
        self.seconds_left = 45
        self.configure_ui(self.seconds_left)
        self.timer.start(1000)
        self.timer_active = True  # Set the flag to True when the timer starts
        print("Timer started/restarted")
        
        
    def update_timer(self):
        self.seconds_left -= 1
        self.configure_ui(self.seconds_left)
        print(f"Timer updated: {self.seconds_left} seconds left")
        if self.seconds_left == 0:
            self.timer.stop()
            self.timer_active = False  # Set the flag to False when the timer stops
            self.close()  # Close the overlay when the timer reaches 0
            print("Overlay closed")
            self.button_tracker.start_detector_timer()  # Restart the detection timer in the ButtonTracker class


class ButtonTracker(QObject):
    def __init__(self, app):
        super().__init__()
        self.overlay = None
        self.app = app
        self.detector = Detector(self.on_detect_callback)  # Create an instance of the Detector class
        self.detector_timer = QTimer(self)
        self.detector_timer.timeout.connect(self.check_detector)
        self.detector_timer.start(500)  # Check every second
        print("ButtonTracker initialized")

    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.middle:
            if pressed:
                print("pressed")
                self.app.postEvent(self.app, QEvent(QEvent.User), Qt.HighEventPriority)
            else:
                print("released")

    def check_detector(self):
        if not self.is_timer_active():  # Check the state of the timer_active flag
            self.detector.detect(None)

    def is_timer_active(self):
        if self.overlay:
            return self.overlay.timer_active
        return False

    def on_detect_callback(self):
        print("Detector callback triggered")
        self.app.postEvent(self.app, QEvent(QEvent.User), Qt.HighEventPriority)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.User:
            self.handle_app_event(event)
            return True
        return False

    def handle_app_event(self, event):
        print("App event received")
        if self.overlay:
            self.overlay.close()
            print("Overlay closed")
        self.overlay = Overlay(self)  # Pass the ButtonTracker instance to the Overlay class
        self.overlay.show()
        print("Overlay shown")
        
    def start_detector_timer(self):
        self.detector_timer.start(250)  # Restart the detection timer
        print("Detection timer restarted")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    button_tracker = ButtonTracker(app)

    mouse_listener = mouse.Listener(on_click=button_tracker.on_click)

    mouse_listener_thread = threading.Thread(target=mouse_listener.start)

    mouse_listener_thread.start()

    app.installEventFilter(button_tracker)
    exit_code = app.exec_()

    mouse_listener.stop()
    
    mouse_listener_thread.join()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()