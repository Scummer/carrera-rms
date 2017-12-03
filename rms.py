""" Carrera(R) Digital 124/132 race management system based on carreralib"""
""" Copyright 2017 Thomas Reich thomas@geekazoids.net """
from PyQt5.QtWidgets import (
     QApplication,
     QWidget,
     QLCDNumber,
     QProgressBar,
     QPushButton,
     QLabel,
     QFrame,
     QVBoxLayout,
     QHBoxLayout,
     QComboBox,
     QGridLayout,
     QShortcut,
     QInputDialog,
     QDialog,
     QListWidget,
     QSizePolicy,
     QTableWidget,
     QTableWidgetItem,
     QMainWindow
)

from PyQt5.QtCore import (
     QTimer,
     QTime,
     QObject,
     Qt
)

from PyQt5.QtBluetooth import (
     QBluetoothDeviceDiscoveryAgent
)

from PyQt5.QtGui import (
     QKeySequence,
     QFont,
     QPainter,
     QColor
)

from carreralib import ControlUnit

import sys

def posgetter(driver):
    return (-driver.lapcount, driver.time)

def formattime(time, longfmt=False):
    if time is None:
        return '0.0'
    s = time // 1000
    ms = time % 1000

    if not longfmt:
        return '%d.%03d' % (s, ms)
    elif s < 3600:
        return '%d:%02d.%03d' % (s // 60, s % 60, ms)
    else:
        return '%d:%02d:%02d.%03d' % (s // 3600, (s // 60) % 60, s % 60, ms)

class BtSelect(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.vLayout = QVBoxLayout(self)
        self.btList = QListWidget()
        self.vLayout.addWidget(self.btList)
        self.hBtnLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hBtnLayout)
        self.scanBtn = QPushButton('Scan')
        self.hBtnLayout.addWidget(self.scanBtn)
        self.connectBtn = QPushButton('Connect')
        self.hBtnLayout.addWidget(self.connectBtn)
        self.rejectBtn = QPushButton('Cancel')
        self.hBtnLayout.addWidget(self.rejectBtn)
        self.connectBtn.clicked.connect(self.accept)
        self.rejectBtn.clicked.connect(self.reject)

class StartLight(QWidget):
    def __init__(self):
        super().__init__()
        self.onVal = False
        self.update()

    def setOn(self, on):
        self.onVal = on
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.onVal:
             painter.setBrush(QColor(40, 40, 40))
        else:
             painter.setBrush(Qt.red)
        painter.drawEllipse(0,0, self.width(), self.height())

class StartLights(QWidget):
    def __init__(self):
        super().__init__()
        hbox = QHBoxLayout(self)
        self.lightOne = StartLight()
        self.lightTwo = StartLight()
        self.lightThree = StartLight()
        self.lightFour = StartLight()
        self.lightFive = StartLight()
        hbox.addWidget(self.lightOne)
        hbox.addWidget(self.lightTwo)
        hbox.addWidget(self.lightThree)
        hbox.addWidget(self.lightFour)
        hbox.addWidget(self.lightFive)
        lightsPal = self.palette()
        lightsPal.setColor(lightsPal.Background, Qt.black)
        self.setPalette(lightsPal)
        self.spacekey = QShortcut(QKeySequence("Space"), self)
        
class Rms(QMainWindow):
    def __init__(self):
        super().__init__()

        self.shutdown = False
        self.btDialog = BtSelect()
        self.discoverCU()
        self.btDialog.scanBtn.clicked.connect(self.discoverCU)
        if self.btDialog.exec_():
            if self.discoverBtDevice.isActive():
                self.discoverBtDevice.stop()
            BTdevice = self.btDialog.btList.selectedItems()
            self.startRMS(BTdevice[0].text().split(' -> ')[1])
        else:
            sys.exit()

    def closeEvent(self, event):
        self.shutdown = True
        self.cu.close()
        event.accept()

    def discoverCU(self):
        self.btDialog.scanBtn.setEnabled(False)
        self.discoverBtDevice = QBluetoothDeviceDiscoveryAgent()
        self.discoverBtDevice.setLowEnergyDiscoveryTimeout(5000)
        self.discoverBtDevice.deviceDiscovered.connect(self.addBtDevice)
        self.discoverBtDevice.finished.connect(self.btScanFinished)
        self.discoverBtDevice.error.connect(self.btScanError)
        self.discoverBtDevice.start()

    def addBtDevice(self, btDevice):
        self.btDialog.btList.addItem(str(btDevice.name()) + ' -> ' + str(btDevice.address().toString()))

    def btScanFinished(self):
        self.btDialog.scanBtn.setEnabled(True)

    def btScanError(self):
        print('bt error')
        sys.exit()

    def startRMS(self, device):
        self.cu = ControlUnit(device, timeout = 1.0)
        self.initUI()

    def initUI(self):
        self.startLights = StartLights()
        rectDesktop = app.desktop().screenGeometry()
        self.startLights.resize(rectDesktop.width()/2, (rectDesktop.width()/2)/5)
        self.setWindowTitle('Race Management System V1.0')
        self.rmsframe = RmsFrame(self.cu)
        self.startLights.spacekey.activated.connect(self.rmsframe.racestart)
        self.setCentralWidget(self.rmsframe)
   
    def run(self):
        last = None
        while True:
            if self.shutdown:
                break
            try:
                data = self.cu.request()
                app.processEvents()
                if data == last:
                    continue
                elif isinstance(data, ControlUnit.Status):
                    self.handle_status(data)
                elif isinstance(data, ControlUnit.Timer):
                    self.handle_timer(data)
                else:
                    pass
                last = data

            except IOError as e:
                if e.errno != errno.EINTR:
                    raise
        sys.exit()


    def handle_status(self, status):
        if status.start > 0 and status.start <= 7:
            self.startLights.show()
            if status.start == 1 or status.start == 2:
                self.startLights.lightOne.setOn(True)
            if status.start == 1 or status.start == 3:
                self.startLights.lightTwo.setOn(True)
            if status.start == 1 or status.start == 4:
                self.startLights.lightThree.setOn(True)
            if status.start == 1 or status.start == 5:
                self.startLights.lightFour.setOn(True)
            if status.start == 1 or status.start == 6:
                self.startLights.lightFive.setOn(True)
            if status.start == 2 or status.start == 7:
                if status.start == 7:
                    self.startLights.lightOne.setOn(False)
                self.startLights.lightTwo.setOn(False)
                self.startLights.lightThree.setOn(False)
                self.startLights.lightFour.setOn(False)
                self.startLights.lightFive.setOn(False)
        else:
            self.startLights.hide()
        for driver, fuel in zip(self.rmsframe.driverArr, status.fuel):
            driver.fuellevel = fuel
        for driver, pit in zip(self.rmsframe.driverArr, status.pit):
            if pit and not driver.pit:
                driver.pitcount += 1
            driver.pit = pit
        self.rmsframe.updateDisplay()
        self.status = status

    def handle_timer(self, timer):
        driver = self.rmsframe.driverArr[timer.address]
        driver.newlap(timer)
        if self.rmsframe.start is None:
            self.rmsframe.start = timer.timestamp
        self.rmsframe.updateDisplay()

class CtrlDialog(QDialog):
    def __init__(self, driverArr):
        super().__init__()
        self.driverArr = driverArr
        self.vlayout = QVBoxLayout(self)
        self.table = QTableWidget(6,2)
        self.vlayout.addWidget(self.table)
        self.table.setHorizontalHeaderLabels(['Driver', 'Controller'])
        for idx, driverObj in enumerate(driverArr):
            if idx < 6:
                ctrlCombobox = QComboBox()
                for ctrlItem in range(1,7):
                    ctrlCombobox.addItem(str(ctrlItem))
                self.table.setItem(idx,0, QTableWidgetItem(driverObj.name))
                ctrlCombobox.setCurrentIndex(idx)
                self.table.setCellWidget(idx,1, ctrlCombobox)
        self.setCtrlBtn = QPushButton('Set Controllers')
        self.closeBtn = QPushButton('Cancel')
        self.hlayout = QHBoxLayout()
        self.vlayout.addLayout(self.hlayout)
        self.hlayout.addWidget(self.setCtrlBtn)
        self.hlayout.addWidget(self.closeBtn)
        self.setCtrlBtn.clicked.connect(self.setNewCtrl)
        self.closeBtn.clicked.connect(self.reject)

    def setNewCtrl(self):
        self.newDriverArr = [None] * 8
        for cellNum in range(0, 8):
            if cellNum < 6:
                self.newDriverArr[int(self.table.cellWidget(cellNum, 1).currentText()) - 1] = self.driverArr[cellNum]
                self.driverArr[cellNum].setCtrlNum(int(self.table.cellWidget(cellNum, 1).currentText()))
            else:
                self.newDriverArr[cellNum] = self.driverArr[cellNum]
        self.accept()
 

class RmsFrame(QFrame):
    def __init__(self, cu):
        super().__init__()
        self.cu = cu
        self.resetRMS()
        self.buildframe()
        self.driverBtn = {}
        self.driverObj = {}
        self.lapcount = {}
        self.totalTime = {}
        self.laptime = {}
        self.bestlaptime = {}
        self.fuelbar = {}
        self.pits = {}

    def buildframe(self):
        self.vLayout = QVBoxLayout(self)
        self.hBtnLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hBtnLayout)
# Add driver to grid
        self.addDriverBtn = QPushButton('(A)dd Driver')
        self.addDriverKey = QShortcut(QKeySequence("a"), self)
        self.hBtnLayout.addWidget(self.addDriverBtn)
        self.addDriverBtn.clicked.connect(self.addDriver)
        self.addDriverKey.activated.connect(self.addDriver)
# Assign Controller
        self.assignCtrlBtn = QPushButton('Assign Controller')
        self.hBtnLayout.addWidget(self.assignCtrlBtn)
        self.assignCtrlBtn.clicked.connect(self.openCtrlDialog)
# Code cars
        self.codeBtn = QPushButton('(C)ode')
        self.codeKey = QShortcut(QKeySequence("c"), self)
        self.hBtnLayout.addWidget(self.codeBtn)
        self.codeBtn.clicked.connect(self.pressCode)
        self.codeKey.activated.connect(self.pressCode)
# Start pace car
        self.paceBtn = QPushButton('(P)ace')
        self.paceKey = QShortcut(QKeySequence("p"), self)
        self.hBtnLayout.addWidget(self.paceBtn)
        self.paceBtn.clicked.connect(self.setPace)
        self.paceKey.activated.connect(self.setPace)
# set Speed
        self.setSpeedBtn = QPushButton('Set (S)peed')
        self.setSpeedKey = QShortcut(QKeySequence("s"), self)
        self.hBtnLayout.addWidget(self.setSpeedBtn)
        self.setSpeedBtn.clicked.connect(self.setSpeed)
        self.setSpeedKey.activated.connect(self.setSpeed)
# set Brakes
        self.setBrakeBtn = QPushButton('Set (B)rake')
        self.setBrakeKey = QShortcut(QKeySequence("b"), self)
        self.hBtnLayout.addWidget(self.setBrakeBtn)
        self.setBrakeBtn.clicked.connect(self.setBrake)
        self.setBrakeKey.activated.connect(self.setBrake)
# Set Fuel
        self.setFuelBtn = QPushButton('Set (F)uel')
        self.setFuelKey = QShortcut(QKeySequence("f"), self)
        self.hBtnLayout.addWidget(self.setFuelBtn)
        self.setFuelBtn.clicked.connect(self.setFuel)
        self.setFuelKey.activated.connect(self.setFuel)
# Reset CU
        self.resetBtn = QPushButton('(R)eset')
        self.resetKey = QShortcut(QKeySequence("r"), self)
        self.hBtnLayout.addWidget(self.resetBtn)
        self.resetBtn.clicked.connect(self.resetRMS)
        self.resetKey.activated.connect(self.resetRMS)
# Start/Pause Race Enter
        self.startRaceBtn = QPushButton('Start Race or Enter changed Settings (Spacebar)')
        self.startRaceBtn.clicked.connect(self.racestart)
        self.spacekey = QShortcut(QKeySequence("Space"), self)
        self.spacekey.activated.connect(self.racestart)
        self.vLayout.addWidget(self.startRaceBtn)
# Driver Grid
        self.vLayout.addLayout(self.buildGrid())

    def buildGrid(self):
        self.mainLayout = QGridLayout()
        self.mainLayout.setSpacing(10)
        self.mainLayout.setHorizontalSpacing(10)
        self.headerFont = QFont()
        self.headerFont.setPointSize(14)
        self.headerFont.setBold(True)
        self.labelArr = ['Pos', 'Driver', 'Total', 'Laps', 'Laptime', 'Best Lap', 'Fuel', 'Pits']
        for index, label in enumerate(self.labelArr):
            self.headerLabel = QLabel(label)
            self.headerLabel.setFont(self.headerFont)
            self.mainLayout.addWidget(self.headerLabel, 0 , index, Qt.AlignHCenter)
        self.mainLayout.setColumnStretch(1, 1)
        self.mainLayout.setColumnStretch(2, 1)
        self.mainLayout.setColumnStretch(3, 2)
        self.mainLayout.setColumnStretch(4, 3)
        self.mainLayout.setColumnStretch(5, 3)
        self.mainLayout.setColumnStretch(6, 2)
        self.mainLayout.setColumnStretch(7, 1)

        return self.mainLayout

    def openCtrlDialog(self):
        self.ctrlDialog = CtrlDialog(self.driverArr)
        if self.ctrlDialog.exec_():
            self.driverArr = self.ctrlDialog.newDriverArr

    def addDriver(self):
        driverRow = self.mainLayout.rowCount()
        if driverRow > 8:
            return
        driver = self.driverArr[driverRow - 1]
        self.posFont = QFont()
        self.posFont.setPointSize(35)
        self.posFont.setBold(True)
        self.driverPos = QLabel(str(driverRow))
        self.driverPos.setStyleSheet("QLabel{ border-radius: 10px; border-color: black; border: 5px solid black; background-color: white}")
        self.driverPos.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.driverPos.setFont(self.posFont)
        self.mainLayout.addWidget(self.driverPos, driverRow, 0)
        self.driverBtn[driverRow] = driver.getNameBtn()
        self.driverBtn[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.driverBtn[driverRow], driverRow ,1)
        self.driverObj[driverRow] = driver
        self.driverBtn[driverRow].clicked.connect(lambda: self.changeDriver(self.driverBtn[driverRow], self.driverObj[driverRow]))
        self.lapcount[driverRow] = driver.getLapCountLCD()
        self.lapcount[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.lapcount[driverRow], driverRow, 3)
        self.totalFont = QFont()
        self.totalFont.setPointSize(25)
        self.totalFont.setBold(True)
        self.totalTime[driverRow] = QLabel('00:00')
        self.totalTime[driverRow].setStyleSheet("QLabel{ border-radius: 10px; border-color: black; border: 5px solid black; background-color: white}")
        self.totalTime[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.totalTime[driverRow].setFont(self.totalFont)
        self.mainLayout.addWidget(self.totalTime[driverRow], driverRow, 2)
        self.laptime[driverRow] = driver.getLapLCD()
        self.laptime[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.laptime[driverRow], driverRow, 4)
        self.bestlaptime[driverRow] = driver.getBestLapLCD()
        self.bestlaptime[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.bestlaptime[driverRow], driverRow, 5)
        self.fuelbar[driverRow] = driver.getFuelBar()
        self.fuelbar[driverRow].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.mainLayout.addWidget(self.fuelbar[driverRow], driverRow, 6)
        self.pits[driverRow] = driver.getPits()
        self.pits[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.mainLayout.addWidget(self.pits[driverRow], driverRow, 7)

    def racestart(self):
        self.cu.start()
#        self.mainLayout.itemAtPosition(1, 5).widget().setPits('Pit')
#        self.mainLayout.itemAtPosition(1, 5).widget().setPits('Track')

    def resetRMS(self):
        if hasattr(self, 'driverArr'):
            for driverObj in self.driverArr:
                driverObj.deleteLater()
        self.start = None
        self.driverArr = [RmsDriver(num) for num in range(1, 9)]

        # discard remaining timer messages
        status = self.cu.request()
        while not isinstance(status, ControlUnit.Status):
            status = self.cu.request()
        self.status = status
        # reset cu timer
        self.cu.reset()

        if hasattr(self, 'mainLayout'):
            while True: 
                widgetToRemove = self.mainLayout.takeAt(0)
                if widgetToRemove == None:
                    break
                widgetToRemove.widget().deleteLater()
            mainItem = self.vLayout.takeAt(2)
            self.vLayout.removeItem(mainItem)
            mainItem.deleteLater()
            self.vLayout.addLayout(self.buildGrid())

    def pressCode(self):
        print('press Code')
        self.cu.request(b'T8')

    def setFuel(self):
        print('set fuel')
        self.cu.request(b'T7')

    def setPace(self):
        print('pace car')
        self.cu.request(b'T1')

    def setSpeed(self):
        print('set speed')
        self.cu.request(b'T5')

    def setBrake(self):
        print('set brake')
        self.cu.request(b'T6')

    def changeDriver(self, driverButton, driverObj):
        self.driverChangeText = QInputDialog.getText(self, 'Change driver name', 'Driver Name', 0, driverButton.text().split('\n')[0])
        if self.driverChangeText[1] == True:
            driverButton.setText(self.driverChangeText[0] + '\n' + 'Ctrl: ' + str(driverObj.CtrlNum))
            driverObj.name = self.driverChangeText[0]

    def updateDisplay(self):
        driversInPlay = [driver for driver in self.driverArr if driver.time]
        if len(driversInPlay) + 1 > self.mainLayout.rowCount():
            self.addDriver()
        for pos, driver in enumerate(sorted(driversInPlay, key=posgetter), start=1):
            if pos == 1:
                leader = driver
                t = formattime(driver.time - self.start, True)
            elif driver.lapcount == leader.lapcount:
                t = '+%ss' % formattime(driver.time - leader.time)
            else:
                gap = leader.lapcount - driver.lapcount
                t = '+%d Lap%s' % (gap, 's' if gap != 1 else '')
            self.driverBtn[pos].setText(driver.name + '\n' + 'Ctrl: ' + str(driver.CtrlNum))
            self.totalTime[pos].setText(t)
            self.lapcount[pos].display(driver.lapcount)
            self.laptime[pos].display(formattime(driver.lapTime))
            self.bestlaptime[pos].display(formattime(driver.bestLapTime))
            self.fuelbar[pos].setValue(driver.fuellevel)
            if driver.fuellevel > 0:
                self.fuelbar[pos].setStyleSheet("QProgressBar{ color: white; background-color: black; border: 5px solid black; border-radius: 10px; text-align: center}\
                                                 QProgressBar::chunk { background: qlineargradient(x1: 1, y1: 0.5, x2: 0, y2: 0.5, stop: 0 #00AA00, stop: " + str(0.92 - (1 / (driver.fuellevel))) + " #22FF22, stop: " + str(0.921 - (1 / (driver.fuellevel))) + " #22FF22, stop: " + str(1.001 - (1 / (driver.fuellevel))) + " red, stop: 1 #550000); }")
            self.pits[pos].display(driver.pitcount)
        
class RmsDriver(QObject):
    def __init__(self, driverNum):
        super().__init__()
        self.CtrlNum = driverNum
        self.name = 'Driver ' + str(driverNum)
        self.lapcount = 0
        self.bestLapTime = None
        self.lapTime = None
        self.time = None
        self.fuellevel = 15
        self.pitcount = 0
        self.pit = False
        self.buildDriver()

    def buildDriver(self):
        self.nameFont = QFont()
        self.nameFont.setPointSize(20)
        self.nameFont.setBold(True)
        self.nameBtn = QPushButton(self.name + '\n' + 'Ctrl: ' + str(self.CtrlNum))
        self.nameBtn.setToolTip('Click to change driver name')
        self.nameBtn.setFont(self.nameFont)
        self.nameBtn.setStyleSheet("QPushButton { border: 5px solid black; border-radius: 10px; background-color: white}")

        self.lapCountLCD = QLCDNumber(3)
        self.lapCountLCD.setStyleSheet("QLCDNumber{ border-radius: 10px; background-color: black}")
        lcdPalette = self.lapCountLCD.palette()
        lcdPalette.setColor(lcdPalette.WindowText, QColor(255, 255, 0))
        self.lapCountLCD.setPalette(lcdPalette)
        self.lapCountLCD.display(self.lapcount)

        self.bestLapLCD = QLCDNumber()
        self.bestLapLCD.setStyleSheet("QLCDNumber{ border-radius: 10px; background-color: black}")
        lcdPalette = self.bestLapLCD.palette()
        lcdPalette.setColor(lcdPalette.WindowText, QColor(255, 255, 0))
        self.bestLapLCD.setPalette(lcdPalette)
        self.bestLapLCD.display(self.bestLapTime)

        self.lapLCD = QLCDNumber()
        self.lapLCD.setStyleSheet("QLCDNumber{ border-radius: 10px; background-color: black}")
        lcdPalette = self.lapLCD.palette()
        lcdPalette.setColor(lcdPalette.WindowText, QColor(255, 255, 0))
        self.lapLCD.setPalette(lcdPalette)
        self.lapLCD.display(self.lapTime)

        self.fuelbar = QProgressBar()
        self.fuelbar.setOrientation(Qt.Horizontal)
        self.fuelbar.setStyleSheet("QProgressBar{ color: white; background-color: black; border: 5px solid black; border-radius: 10px; text-align: center}\
                                    QProgressBar::chunk { background: qlineargradient(x1: 1, y1: 0.5, x2: 0, y2: 0.5, stop: 0 #00AA00, stop: " + str(0.92 - (1 / (self.fuellevel))) + " #22FF22, stop: " + str(0.921 - (1 / (self.fuellevel))) + " #22FF22, stop: " + str(1.001 - (1 / (self.fuellevel))) + " red, stop: 1 #550000); }")
        self.fuelbar.setMinimum(0)
        self.fuelbar.setMaximum(15)
        self.fuelbar.setValue(self.fuellevel)

        self.pitCountLCD = QLCDNumber(2)
        self.pitCountLCD.setStyleSheet("QLCDNumber{ border-radius: 10px; background-color: black}")
        lcdPalette = self.pitCountLCD.palette()
        lcdPalette.setColor(lcdPalette.WindowText, QColor(255, 0, 0))
        self.pitCountLCD.setPalette(lcdPalette)
        self.pitCountLCD.display(self.pitcount)
   
    def getName(self):
        return self.name

    def getNameBtn(self):
        return self.nameBtn

    def getLapCountLCD(self):
        return self.lapCountLCD

    def getBestLapLCD(self):
        return self.bestLapLCD
    
    def getLapLCD(self):
        return self.lapLCD

    def getFuelBar(self):
        return self.fuelbar

    def setCtrlNum(self, num):
        self.CtrlNum = num
        self.nameBtn.setText(self.name + '\n' + 'Ctrl: ' + str(self.CtrlNum))

    def getPits(self):
        return self.pitCountLCD

    def newlap(self, timer):
        if self.time is not None:
            self.lapTime = timer.timestamp - self.time
            if self.bestLapTime is None or self.lapTime < self.bestLapTime:
                self.bestLapTime = self.lapTime
            self.lapcount += 1
        self.time = timer.timestamp
        

if __name__ == '__main__':
    app = QApplication(sys.argv)

    w = Rms()
    w.showMaximized()
    w.run()

    sys.exit(app.exec_())
