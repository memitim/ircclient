import sys
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
        self.connectButton.clicked.connect(self.init_connection)
        self.submitBox.returnPressed.connect(self.submit_text)

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.threads = []
        self.channel = str(self.config['Settings']['Channel'])
        self.nick = str(self.config['Settings']['Nick'])
        self.realName = str(self.config['Settings']['RealName'])

    def init_connection(self):
        print("Creating connection")
        connection = MessageThread()
        # Have to add thread to a list or get a buffer overrun. So much why...
        self.threads.append(connection)
        connection.lineReader.connect(self.parse_line)
        self.senderObject = MessageSender()
        self.senderObject.moveToThread(connection)
        self.senderObject.lineSender.connect(connection.submit_message)
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
            nick = self.nick
            real = self.realName
            NickString = "NICK " + nick + "\r\n"
            UserString = "USER " + nick + " 1 1 1 :" + real + "\r\n"
            self.send_line(NickString)
            self.send_line(UserString)
            outLine = outLine + " User info sent"
            print("Sent response")
        if messageList[-1] == "+i":
            print("Joining channel")
            ChanJoinString = "JOIN " + self.channel + "\r\n"
            outLine = outLine + " " + ChanJoinString
            self.send_line(ChanJoinString)

        self.textWindow.append(outLine)

    def submit_text(self):
        if self.submitBox.text() == "":
            pass
        else:
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
                finalText = "PRIVMSG " + self.channel + " :" + messageText + "\r\n"
                self.textWindow.append("<" + self.nick + "> " + messageText)
            self.send_line(finalText)
            if self.chkEcho.isChecked():
                print("messageText: " + messageText)
                print("finalText: " + finalText)
            self.submitBox.clear()

    def send_line(self, messageText):
        self.senderObject.lineSender.emit(messageText)


class MessageSender(QObject):
    lineSender = pyqtSignal(object)


class MessageThread(QThread):
    lineReader = pyqtSignal(object)

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.ircServer = str(self.config['Settings']['IrcServer'])
        self.portNumber = int(self.config['Settings']['PortNumber'])
        self.SockObj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ReadBuffer = ""
        QThread.__init__(self)
        self.start()

    def run(self):
        print("Preparing to connect")
        self.connect_server()

    def connect_server(self):
        """Connect to IRC server"""
        resp = self.SockObj.connect((self.ircServer, self.portNumber))
        print(f"Response: {resp}")
        while 1:
            self.update_messages()

    def update_messages(self):
        """Get new batch of messages from the message buffer"""
        self.ReadBuffer = self.ReadBuffer + self.SockObj.recv(1024).decode('utf-8')
        BufferList = self.ReadBuffer.split("\n")
        self.ReadBuffer = BufferList.pop()

        for CurrentLine in BufferList:
            TrimmedLine = CurrentLine.rstrip()
            print(f"Current line in buffer: {TrimmedLine}")
            self.lineReader.emit(TrimmedLine)

    def submit_message(self, messageText):
        """Send message to IRC server"""
        self.SockObj.send(messageText.encode('utf-8'))


def main():
    app = QApplication(sys.argv)
    frame = MainWindow()
    frame.show()
    app.exec_()

if __name__ == '__main__':
    main()