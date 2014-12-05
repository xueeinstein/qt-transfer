#!/usr/bin/env python

import sys
import os
import logging
import json
import urllib
import urllib2
import socket
import time
import hashlib
import select
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *

import config
import assets_rc

class bcolors:
    """ set print color """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

class PyJs(QWebPage):
    """
    Makes it possible to use a Python logger to print javascript console messages
    """
    def __init__(self, window, logger=None, parent=None):
        super(PyJs, self).__init__(parent)
        if not logger:
            logger = logging
        self.logger = logger
        self.ctrl = Controller(window)

    def javaScriptConsoleMessage(self, msg, lineNumber, sourceID):
        if sourceID == "qrc:/":
            self.ctrl.resolve(msg)
            self.logger.warning("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))
        else:
            self.logger.warning("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))
        return

class Controller(QObject):
    """Controller class"""
    def __init__(self, window):
        super(Controller, self).__init__()
        self.window = window
        self.dir = os.getcwd()
        # record last that the file-net data updated, init 0
        self.lastUpdateTime = 0
        # create the side daemon process for controller
        self.daemon_thread = DaemonThread()
        # setup signals
        self.connect(self.daemon_thread, SIGNAL("daemonCtrl(QString)"), self.resolve)

    def resolve(self, msg):
        """ classify action """
        msg = str(msg)
        print "msg in resolve:", msg
        action = msg.split('->')[0]
        print "action:", action
        if action == "redirect":
            msg_list = msg.split('->')
            dest = msg_list[1]
            # if login success, start the daemon process
            if dest == "ctrlpanel" and len(msg_list) == 3:
                print "daemon_thread start..."
                self.window.callback.registerUser(msg_list[2])
                self.daemon_thread.register(msg_list[2])
                self.daemon_thread.start()
            
            self.redirect(dest)
        elif action in ("signup", "login", "updateFiles"):
            self.post(msg)
        elif action == "error":
            self.error(msg.split('->')[1])
        elif action == "data":
            return msg.split('->')[1]
        else:
            pass
        return

    def redirect(self, dest):
        if dest in config.router:
            try:
                print os.getcwd()
                viewDir = self.dir + "/" + config.router[dest]
                html = open(viewDir).read()
            except Exception, e:
                raise e
            # if it's control-panel, update file-net data
            if dest == "ctrlpanel":
                msg = '{"action": "queryFilesData", "lastUpdateTime": 0}'
                msg = "queryFilesData->" + msg
                file_net_data = self.post(msg)
                print "Get file-net data", file_net_data
                self.lastUpdateTime = time.time()
                # record files update time in daemon thread
                self.daemon_thread.updateFilesTime(self.lastUpdateTime)
                self.window.callback.getFilesNetData(file_net_data)
            self.window.customSetHtml(html)
        else:
            self.window.callback.cometError("No router!");
            print "no router"
        return

    def post(self, msg):
        # get dict msg from json
        print "post msg:", msg
        action = msg.split('->')[0]
        attr_json_str = msg.split('->')[1]
        msg_dict = json.loads(attr_json_str)
        msg_dict['action'] = action
        # print msg_dict
        # encode and post
        encoded_args = urllib.urlencode(msg_dict)
        url = "http://" + config.signal_server_host + \
            ":" + str(config.signal_server_port)
        res = urllib2.urlopen(url, encoded_args).read()
        print "response msg:", res
        return self.resolve(res)

    def error(self, err):
        self.window.callback.cometError(err)
        return

class Callback(QObject):
    """Callback to font-end"""
    def __init__(self, Qo):
        super(Callback, self).__init__(Qo)
        self.window = Qo
        self.err = ""
        self.data = ""
        self.user = ""
        self.fileAddr = ""

    def cometError(self, err):
        self.err = err
        print "cometError"
        self.window.view.page().mainFrame().\
            evaluateJavaScript(QString("checkErr()"))
        return

    def getFilesNetData(self, data):
        self.data = data
        return

    def registerUser(self, user):
        self.user = user
        return

    @pyqtSlot(result=str)
    def user(self):
        return self.user

    @pyqtSlot(result=str)
    def data(self):
        return self.data

    @pyqtSlot(result=str)
    def error(self):
        return self.err

    @pyqtSlot(result=str)
    def fileInfo(self):
        res = self.fileAddr
        if self.fileAddr != "":
            size = os.path.getsize(self.fileAddr)
            res = "%s %d bytes" %(res, size)
        return res

    @pyqtSlot()
    def filePicker(self):
        fname = QFileDialog.getOpenFileName(self.window, 'Select file')
        if fname:
            # print "selected file:", type(fname), fname
            self.fileAddr = str(fname)
            self.window.view.page().mainFrame().\
                evaluateJavaScript(QString("showFileInfo()"))


class DaemonThread(QThread):
    """
    DaemonProc, to communicate with signal server, 
    as heart beat and signal exchanger
    """
    def __init__(self, parent=None):
        QThread.__init__(self)
        # set as daemon process
        self.id = ""
        self.addr = (config.signal_server_host, config.signal_server_port_udp)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.localFiles = []
        self.filesDataLastUpdate = 0

    def run(self):
        while True:
            self.sendUdpHeartBeat("%s:active"%self.id)
            self.recvFromServer()
            self.scanLocalFiles()
            time.sleep(2)

    def register(self, msg):
        self.id = msg
        print "register:", msg

    def updateFilesTime(self, time):
        self.filesDataLastUpdate = time

    def scanLocalFiles(self):
        """ 
        scan local files, if changed,
        update localFiles and call http send to update remote record
        """
        # change dir into transferDir
        # temporarily, only support files in transferDir, no folder
        # To do: optimize files change, metric by file content md5, not name
        # To do: msg, could be compressed ! e.g. only show add new files, and delete files
        os.chdir(config.transferDir)
        files_list = os.listdir('.')
        getmd5 = lambda x: hashlib.md5(open(x).read()).hexdigest()
        msg_dict = dict()
        msg_dict['name'] = self.id
        msg_dict['files'] = []
        for e in files_list:
            tmp_dict = dict()
            tmp_dict['name'] = e
            tmp_dict['key'] = getmd5(e)
            msg_dict['files'].append(tmp_dict)

        os.chdir('..')
        if cmp(files_list, self.localFiles) != 0:
            # local files changed
            msg = "updateFiles->" + json.dumps(msg_dict)
            print bcolors.OKBLUE + "To signal server: " + msg + bcolors.ENDC
            self.emit(SIGNAL("daemonCtrl(QString)"), msg)
            # update local files record
            self.localFiles = files_list
        return

    def sendUdpHeartBeat(self, msg):
        self.sock.sendto(msg, self.addr)
        print bcolors.OKGREEN + "send UDP heart beat" + bcolors.ENDC
        # self.emit(SIGNAL("daemonCtrl(QString)"), "redirect->recvfile")
        return


    def recvFromServer(self):
        ready = select.select([self.sock], [], [], 6)
        if ready[0]:
            data, server = self.sock.recvfrom(4096)
            print bcolors.OKGREEN +"Recv: "+ data + bcolors.ENDC
            if data != "Ok":
                serverTime = float(data)
                if serverTime > self.filesDataLastUpdate:
                    self.emit(SIGNAL("daemonCtrl(QString)"), "redirect->ctrlpanel")
        else:
            print bcolors.OKGREEN + "server disconnect" + bcolors.ENDC
            # alert users
            self.emit(SIGNAL("daemonCtrl(QString)"), "error->disconnect")
        
class MainWindow(QWidget):
    """ define main window """
    def __init__(self):
        super(MainWindow, self).__init__()
        self.view = QWebView(self)
        self.view.setPage(PyJs(self))
        self.callback = Callback(self)
        self.jsObjs = dict()
        
        self.resize(800, 600)
        self.setFixedSize(self.size())
        self.setWindowTitle('qt-transfer')

    def customSetHtml(self, html, jsLink="callback", qtLink="self.callback"):
        # record into dict
        self.jsObjs[jsLink] = eval(qtLink)
        self.view.setHtml(html, QUrl('qrc:/'))

    @pyqtSlot(str, str)
    def onPopularJavaScriptWindowObject(self):
        for jsObj in self.jsObjs:
            self.view.page().mainFrame().\
                addToJavaScriptWindowObject(jsObj, self.jsObjs[jsObj])

        
if __name__ == "__main__":
    print "============================================"
    print "                 " + bcolors.BOLD + "qt-transfer"+ bcolors.ENDC 
    print "  "+bcolors.FAIL+"Notice:"+bcolors.ENDC+" this CLI output helps your"
    print "    "
    # print "  Notice: this CLI output helps your        "
    print "  This "+bcolors.OKBLUE+"color"+bcolors.ENDC+" highlights HTTP pipline output"
    print "     HTTP, controls view render"
    print "  This "+bcolors.OKGREEN+"color"+bcolors.ENDC+" highlights UDP pipline output"
    print "     UDP, comet status"
    print "  This "+bcolors.WARNING+"color"+bcolors.ENDC+" highlights TCP pipline output"
    print "     TCP, transfer files"
    print "============================================"

    # render app
    app = QApplication(sys.argv)
    window = MainWindow()
    html = open(config.router["login"]).read()
    window.show()
    # window.view.setHtml(html, QUrl('qrc:/'))
    window.customSetHtml(html)
    window.view.page().mainFrame().\
                javaScriptWindowObjectCleared.connect(\
                    window.onPopularJavaScriptWindowObject)
    sys.exit(app.exec_())
