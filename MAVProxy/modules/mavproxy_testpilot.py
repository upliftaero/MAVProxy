"""
  MAVProxy Test Pilot module for gathering data and characterizing aircraft performance

 Author: Mark Jacobsen
"""

# TODO integrate directory setting
# TODO fix naming convention for test numbers


from pymavlink import mavutil
import re, os, sys, time
import csv
import statsmodels.api as sm
import numpy
import pandas
from pandas.io.parsers import *
import matplotlib.pyplot as plt
import math

lowess = sm.nonparametric.lowess
takeoff_epsilon = 2

from MAVProxy.modules.lib import live_graph

from MAVProxy.modules.lib import mp_module

class TestPilotModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(TestPilotModule, self).__init__(mpstate, "testpilot", "advanced logging for performance analysis")
        self.timespan = 20
        self.tickresolution = 0.2
        self.graphs = []

        #self.templates = []
        #self.templates.append(["csv","TPActivityCSV"])
        #self.templates.append(["power","TPActivityPower"])
        self.templates = {'csv':TPActivityCSV,
                          'power':TPActivityPower,
                          'takeoff':TPActivityTakeoff}

        # TestPilot module variables
        self.activities = []
        self.aircraft = ""
        self.prop = ""
        self.motor = ""
        self.weight = ""
        self.comment = ""
        self.directory = os.getcwd()

        self.add_command('tp',self.cmd_testpilot,"      record for analysis","<start|stop|title|comment>")

    def cmd_testpilot(self, args):
        # With no arguments, display status
        if len(args) == 0:
            self.testpilot_show_status()
        elif args[0] == "help":
            print("start <activity name> <label>")
            print("stop <number|activity number>")
            print("directory <directory name>")
            print("aircraft <aircraft name>")
            print("weight <aircraft weight>")
            print("motor <motor name>")
            print("prop <prop name>")
            print("comment <comment>")
        elif args[0] == "start":
            self.testpilot_start_activity(args)
        elif args[0] == "stop":
            self.testpilot_stop_activity(args)
        elif args[0] == "directory":
            self.directory = ' '.join(args[1:])
            print("Directory set: " + self.directory)
        elif args[0] == "aircraft":
            self.aircraft = ' '.join(args[1:])
            print("Aircraft set: " + self.aircraft)
        elif args[0] == "weight":
            self.weight = ' '.join(args[1:])
            print("Weight set: " + self.weight)
        elif args[0] == "motor":
            self.motor = ' '.join(args[1:])
            print("Motor set: " + self.motor)
        elif args[0] == "prop":
            self.prop = ' '.join(args[1:])
            print("Prop set: " + self.prop)
        elif args[0] == "comment":
            self.comment = ' '.join(args[1:])
            print("Comment set: " + self.comment)

    def testpilot_show_status(self):
        print("TestPilot module configuration:")
        print("Working directory: " + self.directory + "\n")
        print("Aircraft type:     " + self.aircraft + "\n")
        print("Weight:            " + self.weight + "\n")
        print("Motor:             " + self.motor + "\n")
        print("Prop:              " + self.prop + "\n")
        print("Comment:           " + self.comment + "\n")
        print("----------------------------------\n")
        print("Activities in progress:\n")
        for i in range(0,len(self.activities)):
            print("(" + str(i) + ") " + self.activities[i].label + " - " + self.activities[i].type + "\n")

    def testpilot_start_activity(self, args):
        if len(args) < 3:
            print("usage: start <activity type> <label>")
            print("Available activities:")
            for k in self.templates.keys():
                print("  " + k)
            return

        activityname = args[1]
        label = args[2]
        for key in self.templates.keys():
            if key == activityname:
                instance = self.templates[key](self,label,self.directory)
                self.activities.append(instance)
                break

    def testpilot_stop_activity(self, args):
        tostop = args[1]
        # Try stopping by label and then by activity number
        for activity in self.activities:
            if tostop == activity.label:
                print("Stopping activity by name: " + tostop)
                activity.kill()
                self.activities.remove(activity)
                return
        print("Stopping activity by number: " + tostop)
        try:
            i = int(tostop)
            self.activities[i].kill()
            self.activities.remove(self.activities[i])
            return
        except:
            print("Error stopping activity by number: " + tostop)

    def unload(self):
        '''unload module'''
        for activity in self.activities:
            activity.kill()
        self.activities = []

    def mavlink_packet(self, msg):
        for activity in self.activities:
            activity.add_mavlink_packet(msg)

def init(mpstate):
    '''initialise module'''
    return TestPilotModule(mpstate)

class TestPilotActivity(object):
    def __init__(self,state,label):
        self.state = state
        return

    def kill(self):
        return

    def add_mavlink_packet(self, msg):
        return

class TPActivityCSV(TestPilotActivity):
    def __init__(self,state,label,fields,directory):
        super(TPActivityCSV, self).__init__(state,label)
        self.fields = fields
        self.state = state
        self.field_types = []
        self.msg_types = set()
        self.filename = directory + os.sep + label + ".csv"
        self.starttime = time.time()
        self.label = label
        #self.name = label + " (csv)"

        re_caps = re.compile('[A-Z_][A-Z0-9_]+')
        for f in self.fields:
            caps = set(re.findall(re_caps, f))
            self.msg_types = self.msg_types.union(caps)
            self.field_types.append(caps)

        print(type(self.fields))

        self.values = [None] * (len(self.fields)+1)

        print("Filename: " + self.filename)
        try:
            self.csvfile = open(self.filename, 'wb')
            self.writer = csv.writer(self.csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
            header = list(self.fields)
            header.insert(0,"time")
            self.writer.writerow(header)
        except Exception as e:
            print("Error opening CSV recording file")
            print(e.message)

    def kill(self):
        self.csvfile.close()

    def add_mavlink_packet(self, msg):
        mtype = msg.get_type()
        if mtype not in self.msg_types:
            return
        self.values[0] = time.time() - self.starttime

        for i in range(len(self.fields)):
            #print("Matching " + str(mtype) + ", " + str(self.field_types[i]))
            if mtype not in self.field_types[i]:
                continue
            f = self.fields[i]
            self.values[i+1] = mavutil.evaluate_expression(f, self.state.master.messages)
        self.writer.writerow(self.values)


class TPActivityPower(TPActivityCSV):
    def __init__(self,state,label,directory):
        _fields = ["SYS_STATUS.current_battery", "SYS_STATUS.voltage_battery", "VFR_HUD.airspeed"]
        super(TPActivityPower, self).__init__(state, label, _fields, directory)
        self.type = "power"
        print("Beginning power response test\nUse 'tp stop <number> to indicate completion")

    def kill(self):
        super(TPActivityPower, self).kill()
        print("Terminating power activity")

        _data = read_csv(self.filename)
        print(_data.head())
        yvalues = _data['SYS_STATUS.current_battery']/100.0*_data['SYS_STATUS.voltage_battery']/1000.0
        xvalues = _data['VFR_HUD.airspeed']
        yline = lowess(yvalues,xvalues,return_sorted=False)

        plt.plot(xvalues,yvalues,'.',color='0.9')
        plt.plot(xvalues,yline,'r',linewidth=3.0)
        title_str = "Power Required vs Airspeed"
        plt.title(title_str)
        plt.xlabel("Airspeed (m/s)")
        plt.ylabel("Watts Required (W)")
        plt.show()
        # TODO: save to file?

class TPActivityTakeoff(TPActivityCSV):
    def __init__(self,state,label,directory):
        _fields = ["VFR_HUD.alt", "GLOBAL_POSITION_INT.lat", "GLOBAL_POSITION_INT.lon"]
        super(TPActivityTakeoff, self).__init__(state, label, _fields, directory)
        self.type = "takeoff"
        print("Beginning takeoff performance test\nUse 'tp stop <number> to indicate completion")

    def kill(self):
        super(TPActivityTakeoff, self).kill()
        print("Terminating takeoff activity")

        _data = read_csv(self.filename)
        print(_data.head())
        _data['distance'] = 0
        print("A")
        # Record the starting coordinates
        #print(_data['GLOBAL_POSITION.lat'])
        try:
            lat1 = _data['GLOBAL_POSITION_INT.lat'][1]/10000000.0
            lon1 = _data['GLOBAL_POSITION_INT.lon'][1]/10000000.0
        except Exception as e:
            print(e.message)
        print("B")
        print("Start lat: " + str(lat1))
        print("Start lon: " + str(lon1))
        print("C")

        # Find the first row that is 'takeoff_epsilon' away from
        # the starting coordinates, indicating the takeoff has
        # started
        start_row = -1
        print("Rows: " + str(_data['time'].count()))
        for i in range(2,_data['time'].count()):
            print("Loop " + str(i))
            try:
                lat2 = _data['GLOBAL_POSITION.lat'][i]/10000000.0
                lon2 = _data['GLOBAL_POSITION.lon'][i]/10000000.0
                total_dist = measure_distance(lat1,lon1,lat2,lon2)
                if total_dist > takeoff_epsilon and start_row == -1:
                    start_row = i
                _data['distance'][i] = total_dist
            except:
                print("skipping row")
        if start_row == -1:
            print("Error: unable to determine takeoff time")
            return

        print("Start row: " + str(start_row))
        print(_data)

        # TODO: analysis

def measure_distance(lat1,lon1,lat2,lon2):
    # Measures Euclidian distance, not account for Earth's curvature.
    # Sufficient approximation for short distances only
    R = 6371000
    x = (lon2 - lon1) * math.cos(0.5*(lat2+lat1))
    y = lat2 - lat1
    d = R * math.sqrt(x*x + y*y)
    return d
