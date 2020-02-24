import sys, settings
from PyQt5.QtWidgets import (QMainWindow, QApplication)
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from gui import Ui_MainWindow
import socket
import configparser
import datetime


class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.textWindow.setReadOnly(True)
        self.connectButton.clicked.connect(self.initConnection)
        self.submitBox.returnPressed.connect(self.submitText)

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.threads = []
        settings.Channel = str(self.config['Settings']['Channel'])
        settings.IrcServer = str(self.config['Settings']['IrcServer'])
        settings.PortNumber = int(self.config['Settings']['PortNumber'])
        settings.Nick = str(self.config['Settings']['Nick'])
        settings.RealName = str(self.config['Settings']['RealName'])

    def initConnection(self):
        print("Creating connection")
        connection = messageThread()
        # Have to add thread to a list or get a buffer overrun. So much why...
        self.threads.append(connection)
        connection.lineReader.connect(self.parse_line)
        self.senderObject = messageSender()
        self.senderObject.moveToThread(connection)
        self.senderObject.lineSender.connect(connection.submitMessage)
        print("senderObject done")

    def parse_line(self, CurrentLine):
        outLine = datetime.datetime.now().strftime('%X')

        SplitLine = CurrentLine.split(":")
        internalList = (SplitLine[1]).split()
        messageText = ":".join(SplitLine[2:])
        messageList = (SplitLine[-1]).split()
        #print(SplitLine)

        if len(internalList) == 3 and internalList[1] == "PRIVMSG":
            senderString = internalList[0]
            senderList = senderString.split("!")
            senderName = senderList[0]
            outLine = outLine + " <" + senderName + "> " + messageText + "\r\n"
        else:
            outLine = outLine + " " + messageText
        print(SplitLine)
        if SplitLine[0] == "PING ":
            PongLine = "PONG " + SplitLine[1] + "\r\n"
            outLine = outLine + " " + PongLine
            self.send_line(PongLine)
        if messageList[-1] == "response":
            print("Sending response")
            nick = settings.Nick
            real = settings.RealName
            NickString = "NICK " + nick + "\r\n"
            UserString = "USER " + nick + " 1 1 1 :" + real + "\r\n"
            self.send_line(NickString)
            self.send_line(UserString)
            outLine = outLine + " User info sent"
            print("Sent response")
        if messageList[-1] == "+i":
            print("Joining channel")
            ChanJoinString = "JOIN " + settings.Channel + "\r\n"
            outLine = outLine + " " + ChanJoinString
            self.send_line(ChanJoinString)

        self.textWindow.append(outLine)

    def submitText(self):
        messageText = str(self.submitBox.text())
        if messageText[0] == "/":
            if messageText[1:4] == "msg":
                targetName = messageText.split()
                bodyText = " ".join(targetName[2:])
                finalText = "PRIVMSG " + targetName[1] + " :" + bodyText + "\r\n"
            else:
                finalText = messageText[1:] + "\r\n"
                self.textWindow.append(messageText)
        else:
            finalText = "PRIVMSG " + settings.Channel + " :" + messageText + "\r\n"
            self.textWindow.append("<" + settings.Nick + "> " + messageText)
        self.send_line(finalText)
        if self.chkEcho.isChecked():
            print("messageText: " + messageText)
            print("finalText: " + finalText)
        self.submitBox.clear()

    def send_line(self, messageText):
        self.senderObject.lineSender.emit(messageText)


class messageSender(QObject):
    lineSender = pyqtSignal(object)


class messageThread(QThread):
    lineReader = pyqtSignal(object)

    def __init__(self):
        self.IrcServer = settings.IrcServer
        self.PortNumber = settings.PortNumber
        self.SockObj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ReadBuffer = ""
        QThread.__init__(self)
        self.start()

    def run(self):
        print("Preparing to connect")
        self.connectServer()

    def connectServer(self):
        # Buffer overrun if single parens used. Seriously, what the fuck Python?
        resp = self.SockObj.connect((self.IrcServer, self.PortNumber))
        print(resp)
        while 1:
            self.update_messages()

    def update_messages(self):
        self.ReadBuffer = self.ReadBuffer + self.SockObj.recv(1024).decode('utf-8')
        BufferList = self.ReadBuffer.split("\n")
        self.ReadBuffer = BufferList.pop()

        for CurrentLine in BufferList:
            TrimmedLine = CurrentLine.rstrip()
            self.lineReader.emit(TrimmedLine)

    def submitMessage(self, messageText):
        self.SockObj.send(messageText.encode('utf-8'))


def main():
    app = QApplication(sys.argv)
    frame = MainWindow()
    frame.show()
    app.exec_()

if __name__ == '__main__':
    main()