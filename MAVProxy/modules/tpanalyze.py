import csv
import statsmodels.api as sm
import numpy
import pandas
from pandas.io.parsers import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import math

lowess = sm.nonparametric.lowess

class TPAnalyze:
    def __init__(self):
        return

    def build_power_report(self, filename, outfile):
        cells = 4
        amps = 10

        pp = PdfPages(outfile)

        _data = read_csv(filename)
        print(_data.head())
        yvalues = _data['SYS_STATUS.current_battery']/100.0*_data['SYS_STATUS.voltage_battery']/1000.0
        xvalues = _data['VFR_HUD.airspeed']
        yline = lowess(yvalues,xvalues,return_sorted=True)


        endurance_high = amps/(yline[:,1]/(cells*4.2))
        endurance_med = amps/(yline[:,1]/(cells*3.7))
        endurance_low = amps/(yline[:,1]/(cells*3.0))

        range_high = endurance_high * 3.6 * yline[:,0]
        range_med = endurance_med * 3.6 * yline[:,0]
        range_low = endurance_low * 3.6 * yline[:,0]


        # Plot 1: Power
        plt.plot(xvalues,yvalues,'.',color='0.9')
        plt.plot(yline[:,0],yline[:,1],'r',linewidth=3.0)
        title_str = "Power Required vs Airspeed"
        plt.title(title_str)
        plt.xlabel("Airspeed (m/s)")
        plt.ylabel("Watts Required (W)")
        #pp.savefig(plt)
        plt.savefig(pp,format='pdf')
        plt.close()

        # Plot 2: Current vs Airspeed
        #plt.plot(xvalues,yvalues/(cells*4.2),'.',color='0.9')
        plt.plot(yline[:,0],yline[:,1]/(cells*4.2),'g',linewidth=2.0)
        plt.plot(yline[:,0],yline[:,1]/(cells*3.7),'b',linewidth=2.0)
        plt.plot(yline[:,0],yline[:,1]/(cells*3.0),'r',linewidth=2.0)
        title_str = "Current Required vs Airspeed"
        plt.title(title_str)
        plt.xlabel("Airspeed (m/s)")
        plt.ylabel("Current Required (A)")
        plt.legend(['4.2V','3.7V','3.0V'],loc=2)
        plt.savefig(pp,format='pdf')
        plt.close()

         # Plot 3: Endurance vs Airspeed
        #plt.plot(xvalues,yvalues/(cells*4.2),'.',color='0.9')
        plt.plot(yline[:,0],endurance_high,'g',linewidth=2.0)
        plt.plot(yline[:,0],endurance_med,'b',linewidth=2.0)
        plt.plot(yline[:,0],endurance_low,'r',linewidth=2.0)
        title_str = "Endurance vs Airspeed"
        plt.title(title_str)
        plt.xlabel("Airspeed (m/s)")
        plt.ylabel("Endurance (hr)")
        plt.legend(['4.2V','3.7V','3.0V'],loc=1)
        #pp.savefig(plt)
        plt.savefig(pp,format='pdf')
        plt.close()


        # Plot 4: Range vs Airspeed
        #plt.plot(xvalues,yvalues/(cells*4.2),'.',color='0.9')
        plt.plot(yline[:,0],range_high,'g',linewidth=2.0)
        plt.plot(yline[:,0],range_med,'b',linewidth=2.0)
        plt.plot(yline[:,0],range_low,'r',linewidth=2.0)
        title_str = "Range vs Airspeed"
        plt.title(title_str)
        plt.xlabel("Airspeed (m/s)")
        plt.ylabel("Range (km)")
        plt.legend(['4.2V','3.7V','3.0V'],loc=1)
        #pp.savefig(plt)
        plt.savefig(pp,format='pdf')
        plt.close()

        pp.close()


        for i in range(8,35):
            print(str(i) + ", " + str(self.lowess_predict(yline,i)))

    def lowess_predict(self,fitted,value):
        i = 0
        if fitted[i,0] > value:
            return -1

        while value > fitted[i,0]:
            i = i + 1
            if i >= fitted.shape[0]:
                return -1
        return fitted[i,1]




if __name__ == '__main__':
    print("running")
    analyze = TPAnalyze()
    analyze.build_power_report("0.csv","0.pdf")