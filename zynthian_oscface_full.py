#!/usr/bin/python3
# -*- coding: utf-8 -*-
#********************************************************************
# ZYNTHIAN PROJECT: Zynthian Emulator
# 
# This program emulates a Zynthian Box.
# It embed the Zynthian GUI and uses rotary QT widgets to emulate
# the phisical rotary encoders throw the zyncoder library's emulation
# layer.
# 
# Copyright (C) 2015-2016 Fernando Moyano <jofemodo@zynthian.org>
#
#********************************************************************
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
# 
#********************************************************************

# Update: adding OSC to control encoder and button
# first two argument to set data and my data variables

import sys
import signal
import os
from re import findall
from PyQt4 import QtGui
from PyQt4.QtCore import * 
import zynthian_emubox

import threading, time, liblo

OSC_PORT=4567

# FIXME: default sif no arguments

# where is the script that will launch the main UI
WRAPPER_EXEC=sys.argv[1]
# corresponding env varibles
ZYNTHIAN_DIR=sys.argv[2]
ZYNTHIAN_MY_DATA_DIR=sys.argv[3]

class ZynthianQProcess(QProcess):     
    client_window_xid=None

    def __init__(self,zcontainer):
        #Call base class method 
        QProcess.__init__(self)
        #Launch Zynthian GUI
        self.zcontainer=zcontainer
        self.zcontainer_xid=zcontainer.winId()
        self.setProcessChannelMode(QProcess.SeparateChannels); #ForwardedChannels,MergedChannels
        print("Zynthian Container XID: "+str(self.zcontainer_xid))
        QObject.connect(self,SIGNAL("readyReadStandardOutput()"),self,SLOT("readStdOutput()"))
        self.start(WRAPPER_EXEC + " " + ZYNTHIAN_DIR + " " + ZYNTHIAN_MY_DATA_DIR + " " + str(self.zcontainer_xid))
        
    
    #Define Slot Here 
    @pyqtSlot()
    def readStdOutput(self):
        zoutput=str(self.readAllStandardOutput(),encoding='utf-8')
        zoutput=zoutput.replace("FLUSH\n","")
        zoutput=zoutput.replace("FLUSH","")
        zoutput=zoutput.strip()
        if zoutput:
            print(zoutput)
            xids = findall("Zynthian GUI XID: ([\d]+)", zoutput)
            try:
                self.client_window_xid=int(xids[0])
                self.zcontainer.embedClient(self.client_window_xid)
            except:
                pass


class MainWindow(QtGui.QMainWindow):
    zynthian_pid=None
    
    # Pin Configuration (PROTOTYPE-EMU)
    rencoder_pin_a=[4,5,6,7]
    rencoder_pin_b=[8,9,10,11]
    gpio_switch_pin=[0,1,2,3]

    # Rencoder status & last values
    rencoder_status=[0,0,0,0]
    rencoder_lastval=[0,0,0,0]

    def __init__(self):
        super(MainWindow, self).__init__()
        self.init_osc()
        self.ui = zynthian_emubox.Ui_ZynthianEmubox()
        self.ui.setupUi(self)
        # Connect Switches
        self.ui.switch_1.pressed.connect(self.cb_switch_1_pressed)
        self.ui.switch_1.released.connect(self.cb_switch_1_released)
        self.ui.switch_2.pressed.connect(self.cb_switch_2_pressed)
        self.ui.switch_2.released.connect(self.cb_switch_2_released)
        self.ui.switch_3.pressed.connect(self.cb_switch_3_pressed)
        self.ui.switch_3.released.connect(self.cb_switch_3_released)
        self.ui.switch_4.pressed.connect(self.cb_switch_4_pressed)
        self.ui.switch_4.released.connect(self.cb_switch_4_released)
        # Connect Rotary Encoders
        self.ui.rencoder_1.valueChanged.connect(self.cb_rencoder_1_change)
        self.ui.rencoder_2.valueChanged.connect(self.cb_rencoder_2_change)
        self.ui.rencoder_3.valueChanged.connect(self.cb_rencoder_3_change)
        self.ui.rencoder_4.valueChanged.connect(self.cb_rencoder_4_change)
        # Embed Zynthian GUI
        self.zynthian_container = QtGui.QX11EmbedContainer(self.ui.frame_screen)
        self.zynthian_container.setGeometry(QRect(1, 3, 480 ,320))
        if len(sys.argv)>4:
            self.zynthian_pid=int(sys.argv[4])
        else:
            self.start_zynthian()

    def closeEvent(self, event):
        self.close_osc()
        print("EXIT!")
        self.zynthian_process.terminate()
        self.zynthian_process.waitForFinished(5000)
        event.accept()

    def start_zynthian(self):
        self.zynthian_process=ZynthianQProcess(self.zynthian_container)
        self.zynthian_pid=self.zynthian_process.pid()
        print("Zynthian GUI PID: "+str(self.zynthian_pid))

    def cb_switch_pressed(self,i):
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.gpio_switch_pin[i])

    def cb_switch_released(self,i):
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.gpio_switch_pin[i]+1)

    def cb_switch_1_pressed(self):
        self.cb_switch_pressed(0)

    def cb_switch_1_released(self):
        self.cb_switch_released(0)

    def cb_switch_2_pressed(self):
        self.cb_switch_pressed(1)

    def cb_switch_2_released(self):
        self.cb_switch_released(1)

    def cb_switch_3_pressed(self):
        self.cb_switch_pressed(2)

    def cb_switch_3_released(self):
        self.cb_switch_released(2)

    def cb_switch_4_pressed(self):
        self.cb_switch_pressed(3)

    def cb_switch_4_released(self):
        self.cb_switch_released(3)

    def cb_rencoder_change(self,i,v):
        if v>self.rencoder_lastval[i]:
            if self.rencoder_status[i]>=3:
                self.rencoder_status[i]=0
            else:
                self.rencoder_status[i]+=1
        elif v<self.rencoder_lastval[i]:
            if self.rencoder_status[i]<=0:
                self.rencoder_status[i]=3
            else:
                self.rencoder_status[i]-=1
        self.rencoder_lastval[i]=v
        #print("RENCODER CHANGE "+str(i)+" => "+str(v)+" ("+str(self.rencoder_status[i])+")")
        if self.rencoder_status[i]==0:
            os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i])
        elif self.rencoder_status[i]==1:
            os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i])
        if self.rencoder_status[i]==2:
            os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i]+1)
        elif self.rencoder_status[i]==3:
            os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i]+1)

    def cb_rencoder_1_change(self,v):
        self.cb_rencoder_change(0,v)

    def cb_rencoder_2_change(self,v):
        self.cb_rencoder_change(1,v)

    def cb_rencoder_3_change(self,v):
        self.cb_rencoder_change(2,v)

    def cb_rencoder_4_change(self,v):
        self.cb_rencoder_change(3,v)


    def init_osc(self):       
         # create server, listening on port 1234
        try:
            self.server = liblo.Server(OSC_PORT)
        except liblo.ServerError as err:
            print(str(err))
            sys.exit()
    
        # register method taking an int and a float
        self.server.add_method("/zyn/encoder", 'if', self.osc_encoder)
        self.server.add_method("/zyn/press", 'i', self.osc_press)
        self.server.add_method("/zyn/release", 'i', self.osc_release)

        # default callback
        self.server.add_method(None, None, self.osc_fallback)
        # start to listen
        self.stop_event=threading.Event()
        self.c_thread=threading.Thread(target=self.OSCListener, args=(self.stop_event,))
        self.c_thread.start() 
     
    def close_osc(self):
        # terminating OSC thread
        self.stop_event.set()
        self.close()   
        
    def OSCListener(self,stop_event):
        state=True
        while state and not stop_event.isSet():
            self.server.recv(100)

    def osc_press(self, path, args):
        i = args
        print("received press message '%s' with arguments '%d'" % (path, i))
        if i < 0:
            i = 0
        elif i > 3:
            i = 3
        self.cb_switch_press(i)
        
    def osc_release(self, path, args):
        i = args
        print("received release message '%s' with arguments '%d'" % (path, i))
        if i < 0:
            i = 0
        elif i > 3:
            i = 3
        self.cb_switch_release(i)
        
    def osc_encoder(self, path, args):
        i, v = args
        print("received encoder message '%s' with arguments '%d' and '%f'" % (path, i, v))
        
        # sanitize encoder number
        if i < 0:
            i = 0
        elif i > 3:
            i = 3
            
        # sanitize encoder value, don't try to change more than 127
        if v > 127:
            v = 127
        elif v < -127:
            v = -127
        
        # change value
        if v > 0:
            while v > 0:
                self.inc_encoder(i)
                v-=1
        elif v < 0:
            while v < 0:
                self.dec_encoder(i)
                v+=1      
    
    def inc_encoder(self, i):
        print("inc")
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i]+1)
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i]+1)
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i])
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i])
        time.sleep(0.01)

    def dec_encoder(self, i):
        print("dec")
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i]+1)
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i]+1)
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i])
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i])
        time.sleep(0.01)

        
    def osc_fallback(self, path, args, types, src):
        print("got unknown message '%s' from '%s'" % (path, src.url))
        
        for a, t in zip(args, types):
            print("argument of type '%s': %s" % (t, a))
 
        
app = QtGui.QApplication(sys.argv)

my_mainWindow = MainWindow()
my_mainWindow.show()

sys.exit(app.exec_())
