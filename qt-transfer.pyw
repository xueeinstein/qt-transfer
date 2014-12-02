#!/usr/bin/env python

import sys
import logging
import json
import urllib
import urllib2
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *

import config
import assets_rc

""" views
register.html: first-time register, unique username
about.html: about page of qt-transfer
help.html: help page of qt-transfer
controlPanel.html: auto-login and redirect to this page, 
	graph shows available resources 
"""

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
            # self.logger.warning("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))
        else:
            self.logger.warning("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))
        return

class Controller():
    """Controller class"""
    def __init__(self, window):
        self.window = window

    def resolve(self, msg):
        """ classify action """
        msg = str(msg)
        print "msg in resolve:", msg
        action = msg.split('->')[0]
        print "action:", action
        if action == "redirect":
            self.redirect(msg.split('->')[1])
        elif action in ("signup", "login"):
            self.post(msg)
        elif action == "error":
            self.error(msg.split('->')[1])
        else:
            pass
        return

    def redirect(self, dest):
        if dest in config.router:
            try:
                html = open(config.router[dest]).read()
            except Exception, e:
                raise e
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
        self.err = ""

    def cometError(self, err):
        self.err = err
        print "cometError"
        return

    @pyqtSlot(result=str)
    def error(self):
        return self.err

class MainWindow(QWidget):
    """ define main window """
    def __init__(self):
        super(MainWindow, self).__init__()
        self.view = QWebView(self)
        self.callback = Callback(self)
        self.view.setPage(PyJs(self))
        self.jsObjs = dict()
        # self.view.page().mainFrame().\
            # addToJavaScriptWindowObject("callback", self.callback)
        
        self.resize(800, 600)

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
