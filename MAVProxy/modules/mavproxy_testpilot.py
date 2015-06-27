"""
  MAVProxy Test Pilot module for gathering data and characterizing aircraft performance

 Authors:   Mark Jacobsen
            Kevin Wells
"""

# TODO fix naming convention for test numbers - is this complete?

from pymavlink import mavutil
import re, os, sys, time
import csv
#import statsmodels.api as sm
import numpy
import pandas
from pandas.io.parsers import read_csv
import math

from MAVProxy.modules.lib import live_graph
from MAVProxy.modules.lib import mp_module

import tpanalyze

#lowess = sm.nonparametric.lowess
takeoff_epsilon = 2

KEY_AIRCRAFT    = "aircraft"
KEY_WEIGHT      = "weight"
KEY_MOTOR       = "motor"
KEY_PROP        = "prop"
KEY_COMMENT     = "comment"

CONFIG_FILE_EXTENSION       = ".config"
DEFAULT_CONFIG_FILE         = "default" + CONFIG_FILE_EXTENSION

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
        self.configuration = {}
        self.directory = os.getcwd()

        self.add_command('tp',self.cmd_testpilot,"record and analyze flight data","<start|stop|directory|aircraft|weight|motor|prop|comment|write|read>")

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
            print("write # Writes aircraft configuration file")
            print("read  # Reads aircraft configuration file")
        elif args[0] == "start":
            self.testpilot_start_activity(args)
        elif args[0] == "stop":
            self.testpilot_stop_activity(args)
        elif args[0] == "directory":
            self.directory = ' '.join(args[1:])
            print("Directory set: " + self.directory)
        elif args[0] == KEY_AIRCRAFT:
            self.configuration[KEY_AIRCRAFT] = ' '.join(args[1:])
            print("Aircraft set: " + self.configuration[KEY_AIRCRAFT])
        elif args[0] == KEY_WEIGHT:
            self.configuration[KEY_WEIGHT] = ' '.join(args[1:])
            print("Weight set: " + self.configuration[KEY_WEIGHT])
        elif args[0] == KEY_MOTOR:
            self.configuration[KEY_MOTOR] = ' '.join(args[1:])
            print("Motor set: " + self.configuration[KEY_MOTOR])
        elif args[0] == KEY_PROP:
            self.configuration[KEY_PROP] = ' '.join(args[1:])
            print("Prop set: " + self.configuration[KEY_PROP])
        elif args[0] == KEY_COMMENT:
            self.configuration[KEY_COMMENT] = ' '.join(args[1:])
            print("Comment set: " + self.configuration[KEY_COMMENT])
        elif args[0] == "write":
            with open(self.directory + os.sep + DEFAULT_CONFIG_FILE, 'w') as paramfile:
                paramfile.write(str(self.configuration))
        elif args[0] == "read":
            with open(self.directory + os.sep + DEFAULT_CONFIG_FILE, 'r') as paramfile:
                self.configuration = {}
                dict = paramfile.read()
                self.configuration = eval(dict) # This is a security risk
        else:
            print("Invalid command: " + args[0])

    def testpilot_show_status(self):
        print("TestPilot module configuration:")
        print("Working directory: " + self.directory + "\n")
        aircraft = self.configuration[KEY_AIRCRAFT] if KEY_AIRCRAFT in self.configuration else ""
        print("Aircraft type:     " + aircraft + "\n")
        weight = self.configuration[KEY_WEIGHT] if KEY_WEIGHT in self.configuration else ""
        print("Weight:            " + weight + "\n")
        motor = self.configuration[KEY_MOTOR] if KEY_MOTOR in self.configuration else ""
        print("Motor:             " + motor + "\n")
        prop = self.configuration[KEY_PROP] if KEY_PROP in self.configuration else ""
        print("Prop:              " + prop + "\n")
        comment = self.configuration[KEY_COMMENT] if KEY_COMMENT in self.configuration else ""
        print("Comment:           " + comment + "\n")
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
        if (self.find_activity_by_label(label)) is not None:
            print("Activity label already exists: " + label)
            return

        for key in self.templates.keys():
            if key == activityname:
                instance = self.templates[key](self,label,self.directory,self.configuration)
                self.activities.append(instance)
                break

    def testpilot_stop_activity(self, args):
        tostop = args[1]
        # Try stopping by label and then by activity number
        activity = self.find_activity_by_label(tostop)
        if activity is not None:
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

    def find_activity_by_label(self, label):
        for activity in self.activities:
            if label == activity.label:
                return activity

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
    def __init__(self,state,label,fields,directory,configuration):
        super(TPActivityCSV, self).__init__(state,label)
        self.fields = fields
        self.state = state
        self.field_types = []
        self.msg_types = set()
        self.directory = directory
        self.configuration = configuration
        self.filename = label + ".csv"
        self.fullfilename = self.directory + os.sep + self.filename
        self.starttime = time.time()
        self.label = label

        re_caps = re.compile('[A-Z_][A-Z0-9_]+')
        for f in self.fields:
            caps = set(re.findall(re_caps, f))
            self.msg_types = self.msg_types.union(caps)
            self.field_types.append(caps)

        #print(type(self.fields))

        self.values = [None] * (len(self.fields)+1)

        print("Filename: " + self.fullfilename)
        try:
            self.csvfile = open(self.fullfilename, 'wb')
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
    def __init__(self,state,label,directory,configuration):
        _fields = ["SYS_STATUS.current_battery", "SYS_STATUS.voltage_battery", "VFR_HUD.airspeed"]
        super(TPActivityPower, self).__init__(state, label, _fields, directory,configuration)
        self.type = "power"
        print("Beginning power response test\nUse 'tp stop <number|label>' to end the test")  # Move this to superclass?

    def kill(self):
        super(TPActivityPower, self).kill()
        print("Terminating power activity")

        _data = read_csv(self.fullfilename)
        print(_data.head())

        analyzer = tpanalyze.TPAnalyze(self.directory, self.configuration)
        analyzer.build_power_report(self.filename)

"""
        # Old code for putting a plot up in a separate window
        # Note that when this window is up, the simulator is frozen - but it will buffer commands in the console.
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
"""


class TPActivityTakeoff(TPActivityCSV):
    def __init__(self,state,label,directory,configuration):
        _fields = ["VFR_HUD.alt", "GLOBAL_POSITION_INT.lat", "GLOBAL_POSITION_INT.lon"]
        super(TPActivityTakeoff, self).__init__(state, label, _fields, directory, configuration)
        self.type = "takeoff"
        print("Beginning takeoff performance test\nUse 'tp stop <number> to indicate completion")

    def kill(self):
        super(TPActivityTakeoff, self).kill()
        print("Terminating takeoff activity")

        _data = read_csv(self.fullfilename)
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

        lowess = sm.nonparametric.lowess




def measure_distance(lat1,lon1,lat2,lon2):
    # Measures Euclidian distance, not account for Earth's curvature.
    # Sufficient approximation for short distances only
    R = 6371000
    x = (lon2 - lon1) * math.cos(0.5*(lat2+lat1))
    y = lat2 - lat1
    d = R * math.sqrt(x*x + y*y)
    return d
