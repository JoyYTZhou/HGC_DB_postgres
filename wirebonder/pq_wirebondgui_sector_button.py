import sys, csv
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel#, QScroll
from PyQt5.QtCore import Qt, QRectF, QRect
from PyQt5.QtGui import QPainter, QPen, QColor, QRegion, QPainterPath#, pyqtSignal

class TriStateButton(QPushButton):
    def __init__(self, state_counter, state_counter_labels, state_button_labels, label_text, angle_start, angle_span, parent=None):
        super().__init__(parent)
        self.angle_start = angle_start
        self.angle_span = angle_span
        self.state_counter = state_counter
        self.state_counter_labels = state_counter_labels
        self.state_button_labels = state_button_labels
        self.label_text = label_text
        self.state = 0
        self.clicked.connect(self.changeState)

    def changeState(self):
        old_state = self.state
        self.state = (self.state + 1) % 3
        self.state_counter[old_state] -= 1
        self.state_counter[self.state] += 1
        self.updateCounter()
        self.update()

    def updateCounter(self):
        altlab = ['nom','redo','bad']        
        for state, count_label in self.state_counter_labels.items():
            count_label.setText(f"{altlab[state]}: {self.state_counter[state]}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        pen = QPen(Qt.black)
        painter.setPen(pen)
        if self.state == 0:
            painter.setBrush(QColor('#3498db'))
        elif self.state == 1:
            painter.setBrush(Qt.yellow)
        elif self.state == 2:
            painter.setBrush(Qt.red)
        painter.drawPie(rect, int(self.angle_start*16), int(self.angle_span * 16))
        # painter.drawPie(rect, 90*16, int(120 * 16))

        # Draw label
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.label_text)

        # Create a region based on the pie slice shape
        region = QRegion()
        path = QPainterPath()
        path.moveTo(self.width() / 2, self.height() / 2)
        path.arcTo(rect, self.angle_start, self.angle_span)
        region += QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

        # mask_rect = QRect(-5, -5, self.width() + 10, self.height() + 10)  # Adjust the padding as needed
        # region = QRegion(mask_rect, QRegion.Ellipse)
        # region -= QRegion(mask_rect, QRegion.Ellipse)  # Use mask_rect instead of rect
        # self.setMask(region)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Tri-State Buttons")
        self.setGeometry(100, 100, 600, 600)

        self.state_counter = {0: 3, 1: 0, 2: 0}
        self.state_counter_labels = {}
        self.state_button_labels = {}

        altlab = ['nom','redo','bad']
        for state in self.state_counter:
            lab = QLabel(f"{altlab[state]}: {self.state_counter[state]}", self)
            lab.move(20, 0 + state * 20)
            self.state_counter_labels[state] = lab

        # s = 6
        # positions = np.array([[r*np.cos(2*np.pi*i/s),r*np.sin(2*np.pi*i/s)] for i in range(s) for r in [0.15, 0.2,0.35,0.43]])
        
        fname = 'stepholes.csv'
        with open(fname, 'r') as file:
            csvf = csv.DictReader(file)
            positions = np.array([[row['Center X'],row['Center Y (flipped)']] for row in csvf]).astype(float)/200

        
        num_buttons = 3
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = 35  # Radius of the circle
        angle_spans = [120, 120, 120]  # Angle spans for each button
        start_angle = 0  # Initial angle for the first button

        for ind, pos in enumerate(positions):
            button_labels = (np.array([1,2,3])+3*ind).astype(str) # Labels for buttons
            print(button_labels)
            for label_text, angle_span in zip(button_labels, angle_spans):
                button = TriStateButton(self.state_counter, self.state_counter_labels, self.state_button_labels, label_text, start_angle, angle_span, self)
                x = int(pos[0] * self.width() + center_x + 2*np.cos(np.radians(start_angle + angle_span/2))) # Keeps the buttons from overlapping
                y = int(pos[1] * self.height() + center_y - 2*np.sin(np.radians(start_angle + angle_span/2))) # Keeps the buttons from overlapping
                button.setGeometry(x, y, radius, radius)
                button.show()
                start_angle += angle_span

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
