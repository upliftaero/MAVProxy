# TODO implement pipe to pass aircraft name back and forth
# TODO why does UpliftFrame draw button over text
# TODO start tracking aircraft status variables in UpliftFrame
# TODO code status panel
# TODO write mavlink_packet() to pass status codes to UpliftFrame's status panel
# TODO self.master.arducopter_disarm()
# TODO self.master.arducopter_arm()
"""
  Uplift Aeronautics
  Additional GCS features
"""

from pymavlink import mavutil
import re, os, sys

from MAVProxy.modules.lib import live_graph

from MAVProxy.modules.lib import mp_module
from uplift_event import *
import wx, multiprocessing

class UpliftModule(mp_module.MPModule):
    def __init__(self, mpstate):
        self.planename = "aircraft"
        self.upliftframe = None

        parent_pipe, child_pipe = multiprocessing.Pipe()

        super(UpliftModule, self).__init__(mpstate, "uplift", "Uplift Aeronautics GCS features")

        self.add_command('lights', self.cmd_lights, "<on|off> toggle landing lights",
                         ['(VARIABLE)'])
        self.add_command('selfdestruct',self.cmd_selfdestruct, "activate autopilot self-destruct")
        self.add_command('upliftgcs',self.cmd_upliftgcs, "show uplift gcs")
        self.add_command('plane',self.cmd_plane,"set name of active plane")

    def cmd_lights(self, args):
        """
        Toggle landing lights
        """
        if len(args) == 0:
            # list current graphs
            print("Usage: lights <on|off>")
            return

        elif args[0] == "help":
            print("Usage: lights <on|off>")
        elif args[0] == "on":
            # TODO relay 1 on
            self.master.set_relay(1,True)
            #self.master.mav.command_long_send(self.target_system,
            #                                       self.target_component,
            #                                       mavutil.mavlink.MAV_CMD_DO_SET_RELAY, 0,
            #                                       1, 1,
            #                                       0, 0, 0, 0, 0)
            print("landing lights are on")
            return
        elif args[0] == "off":
            # TODO relay 1 off
            self.master.set_relay(1,False)
            #self.master.mav.command_long_send(self.target_system,
            #                                       self.target_component,
            #                                       mavutil.mavlink.MAV_CMD_DO_SET_RELAY, 0,
            #                                       1, 0,
            #                                       0, 0, 0, 0, 0)
            print("landing lights are off")
            return

    def cmd_selfdestruct(self,args):
        # TODO relay 0 on
        self.master.set_relay(0,True)
        #self.master.mav.command_long_send(self.target_system,
        #                                           self.target_component,
        #                                           mavutil.mavlink.MAV_CMD_DO_SET_RELAY, 0,
        #                                           0, 1,
        #                                           0, 0, 0, 0, 0)
        print("self-destruct activated")
        return

    def cmd_plane(self,args):
        if len(args) == 0:
            print("Usage: plane <name>")
            return
        if args[0] == "help":
            print("Usage: plane <name>")
            return
        else:
            self.planename = ' '.join(args[0:])
            print("Aircraft name set: " + self.planename)
            if self.upliftframe != None:
                print("DEBUG inside if")
                #name_event = UpliftEvent(UPLIFT_PLANENAME_CHANGE,self.planename)
                #self.
                #self.upliftframe.set_plane_name(self.planename)


    def cmd_upliftgcs(self,args):
        # TODO: prevent opening multiple windows
        self.child = multiprocessing.Process(target=self.child_task)
        self.child.start()

    def child_task(self):
        app = wx.PySimpleApp()
        app.frame = UpliftFrame(self)
        self.upliftframe = app.frame
        print(type(self.upliftframe))
        app.frame.Show()
        app.MainLoop()
        print("thread done")

    def unload(self):
        '''unload module'''

    def mavlink_packet(self, msg):
        '''handle an incoming mavlink packet'''
        return


def init(mpstate):
    '''initialise module'''
    return UpliftModule(mpstate)

class UpliftFrame(wx.Frame):
    def __init__(self, parent):
        self.parent = parent
        self.planename = parent.planename




        wx.Frame.__init__(self,None, -1, "Uplift Aeronautics GCS Tools")
        panel = wx.Panel(self, -1)

        sizer_master = wx.BoxSizer(wx.VERTICAL)
        sizer_header = wx.BoxSizer(wx.HORIZONTAL)

        sizer_master.Add(sizer_header, wx.EXPAND)
        patch = wx.Image("patch.jpg", wx.BITMAP_TYPE_JPEG).ConvertToBitmap()
        self.patch_jpg = wx.StaticBitmap(self, bitmap=patch)

        self.label_plane = wx.StaticText(self, -1, self.planename)
        font = wx.Font(24, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        self.label_plane.SetFont(font)

        self.disarm_button = wx.Button(self,-1,"Disarm")


        button = wx.Button(self, -1, "Close Me")

        sizer_header.Add(self.patch_jpg,0)
        sizer_header.Add(self.label_plane, 1, wx.EXPAND|wx.CENTER|wx.ALIGN_CENTER)
        sizer_header.Add(self.disarm_button,0)


        sizer_master.Add(button)

        self.Bind(wx.EVT_BUTTON, self.OnCloseMe, button)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

        self.SetSizer(sizer_master)

        self.update_timer = wx.Timer(self)
        #self.Bind(wx.EVT_TIMER, self.on_update_timer, self.on_timer)
        self.update_timer.Start(100)

    def on_timer(self):
         while self.parent.child_pipe.poll():
            uplift_msg = self.parent.child_pipe.recv()
            print("Received: " + uplift_msg.type)

    def set_plane_name(self, planename):
        self.planename = planename
        self.label_plane.SetLabel(planename)
        print("set name")

    def OnCloseMe(self, event):
        self.Close(True)

    def OnCloseWindow(self, event):
        self.Destroy()

class StatusPanel(wx.Panel):
    def __init__(self):
        return

