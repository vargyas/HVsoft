# Leakage current processing application
# file config_win.ini holds the configuration
# should be run with HV.bat on windows
# author: Marton Vargyas
# 2017

from matplotlib.dates import strpdate2num
import ConfigParser
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
#import guidata

colors = ['#FF6666', '#FF0000', '#990000', # RED
          '#6666FF', '#0000FF', '#000099', # BLUE
          '#C0C0C0', '#808080', '#404040', # GRAY
          '#66FF66', '#00CC00', '#009900', # GREEN
          '#FF66FF', '#FF00FF', '#990099', # MAGENTA
          '#FFB266', '#FF8000', '#CC6600', # ORANGE
          '#B266FF', '#9933FF', '#6600CC', # PURPLE
          '#66FFFF', '#00CCCC', '#009999'] # LIGHTBLUE

# class to hold foil-related data
class MFoil:
    def __init__(self, configname, infilename):
        self._infile = infilename
        # read configuration from 'config.ini'
        self._settings = ConfigParser.ConfigParser()
        self._settings.read(configname)
        self._location = int(self._settings.get("settings","kIndex"))

        self._type    = self.GuessType()     # type of GEM, 0=IROC, 1-3=OROC1-3
        self._nc      = self._type * 2 + 18  # number of channels for given type
        self._nraw    = 6                    # number of raws in overview plot, 6 for IROC, 8 for the rest
        if self._type > 0: self._nraw = 8

        self._subtype = self.GuessSubType()  # subtype of GEM, 1-4=G1-G4
        self._name    = self._infile.replace('.txt','') # barcode of the foil
        self._savedir = self._settings.get("settings", "kHVsavedir")
        self._datadir = self._settings.get("settings", "kHVdatadir")

        self._isloaded    = False
        self._isprocessed = False
        
        # data is read to a numpy named array
        self._data = self.LoadFoil()

        # time is zero-padded
        self._times = []
        for i in range(len(self._data[:,0])):
            self._times.append( (self._data[i][0]-self._data[0][0])/3600. )

        # drawing and printing report to pdf
        pdfname = ('{}/Report_HV_{}'.format(self._savedir, self._infile)).replace('.txt','.pdf')
        
        print '\tSaving report:', pdfname, '\n'
        self._report = PdfPages(pdfname)
        self.DrawTimes()
        self.DrawOverviewMean()
        self.DrawOverviewTimes(False)
        self.DrawOverviewTimes(True)
        # ramp-up (approx. fist 10 minutes)
        self.DrawOverviewTimes(False, 600)
        # ramp-down (approx. last 10 minutes)
        self.DrawOverviewTimes(False, -600)
        
        self._report.close()

        # save data to specific format (only for Budapest)
        if self._location == 1:
            self.Save()

    def GuessType(self):
        typ=-1
        if    "I"  in self._infile: typ = 0
        elif  "O1" in self._infile: typ = 1
        elif  "O2" in self._infile: typ = 2
        elif  "O3" in self._infile: typ = 3
        return typ

    def GuessSubType(self):
        subtyp=-1
        if   'G1' in self._infile: subtyp = 1
        elif 'G2' in self._infile: subtyp = 2
        elif 'G3' in self._infile: subtyp = 3
        elif 'G4' in self._infile: subtyp = 4
        return subtyp

    def LoadFoil(self):
        print '\tLoading file:', self._infile, 'with', self._settings.get("settings","kLocation")
        
        if self._location == 1:
			# sometimes 26 columns are saved instead of 25, invalid_raise=False make it to skip over them
            data = np.genfromtxt( os.path.normpath(os.path.join(self._datadir,self._infile)), invalid_raise=False )

            # Loading IROC
            if self._type == 0:
                # first and last channels (along with 2 middle ones) are not connected
                # channels are converted to sectors with this mapping
                conversion = [0, 13, 2, 14, 3, 15, 4, 16, 5, 17, 6, 18, 7, 19, 8, 20, 9, 21, 10, 1, 11, 12, 22, 23, 24]
                
                data = data[:,conversion]
                print '\tloading done'

                return data  
            
            # Loading OROC2
            elif self._type == 2:
                # first and last channels are not connected
                # channels are converted to sectors with this mapping
                conversion = [0, 13, 2, 14, 3, 15, 4, 16, 5, 17, 6, 18, 7, 19, 8, 20, 9, 21, 10, 22, 11, 23, 13, 1, 24]

                data = data[:,conversion]
                return data
                
            else: raise ValueError("For Budapest only IROC and OROC2 is implemented. Something wrong with filename?")   

        elif self._location == 0:
            data = np.genfromtxt(os.path.normpath(os.path.join(self._datadir,self._infile)), skiprows=1, converters = {0:strpdate2num('%Y-%m-%d'), 1: strpdate2num('%H:%M:%S')} )            
            
            # keeping only time and channels from format:
            # Date/C:Time:TimeStamp/D:time:VMeas:IMeas:I_00:I_01:I_02:I_03:I_04:I_05:I_06:I_07:
            # I_08:I_09:I_10:I_11:I_12:I_13:I_14:I_15:I_16:I_17:I_18:I_19:I_20:I_21:I_22:I_23
            conversion = [3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
            
            data = data[:,conversion]
            return data
            
        # load foil data to numpy array and return it
        # Bud/Helsinki convention here
        # only that many channels as in

    def GetInFile(self): return self._infile

    def DrawOverviewTimes(self, yzoom=False, xzoom=0):
        fig, ax = plt.subplots(nrows=self._nraw, ncols=3, sharex=True, sharey=True)
        fig.text(0.5, 0.04, 'time [hour]', ha='center')
        fig.text(0.04, 0.5, 'leakage current [nA]', va='center', rotation='vertical')
        
        for i in range(self._nc):
            index = (i%self._nraw,i/self._nraw)
            
            if xzoom>0:
                ax[index].plot( self._times[:xzoom],self._data[:xzoom,i+1] )
                ax[index].grid(True)
                xmax_l = np.amax( self._times[:xzoom] ) *0.8
                ymin_l = np.amin( self._data[:xzoom,2])*0.8
            else:
                ax[index].plot( self._times[xzoom:],self._data[xzoom:,i+1] )
                ax[index].grid(True)
                xmax_l = np.amax( self._times[xzoom:] ) *0.8
                ymin_l = np.amin( self._data[xzoom:,2])*0.8
                
            if yzoom:
                ax[index].set_ylim([-0.5,0.5])
                ax[index].text(xmax_l, -0.4, 'S{:02d}'.format(i + 1))
            else: ax[index].text(xmax_l, ymin_l, 'S{:02d}'.format(i+1) )
        fig.subplots_adjust(bottom=0.15, left=0.15, hspace=0.05, wspace=0.015)
        
        self._report.savefig(fig)
      
    def DrawTimes(self):
        fig, ax = plt.subplots(2,1, sharex=True)
        fig.text(0.5, 0.04, 'time [hour]', ha='center')
        fig.text(0.04, 0.5, 'leakage current [nA]', va='center', rotation='vertical')
        for iplot in range(2):
            for i in range(self._nc):
                ax[iplot].plot(self._times,self._data[:,i+1], color=colors[i], label='S{:02d}'.format(i+1))
                ax[iplot].grid(True)
                if iplot==1: ax[iplot].set_ylim(-0.5,0.5)
                
        fig.subplots_adjust(bottom=0.15, left=0.15, right=0.8, hspace=0.05, wspace=0.015)
        plt.legend( loc="right", bbox_to_anchor=[1., 1], fontsize="small", mode="expand", borderaxespad=0.)
        self._report.savefig(fig)

    def DrawOverviewMean(self):
        fig, ax = plt.subplots(nrows=self._nraw, ncols=3, sharex=True, sharey=True)
        fig.text(0.5, 0.04, 'leakage current [nA]', ha='center')
        fig.text(0.04, 0.5, 'occurrence', va='center', rotation='vertical')
        for i in range(self._nc):
            index = (i%self._nraw,i/self._nraw)
            #data = self._data['S{:02d}'.format(i+1)]
            ax[index].hist(self._data[:,i+1], bins=np.arange(-0.5, 0.5, 0.005))
            ax[index].grid(True)
            ax[index].text(0.3, 0, 'S{:02d}'.format(i+1) )
            ax[index].set_xlim([-0.5,0.5])
        fig.subplots_adjust(bottom=0.15, left=0.15, hspace=0.05, wspace=0.015)
        
        self._report.savefig(fig)     

    def Save(self):
        dataname = ('{}/{}_sectors.txt'.format(self._savedir, self._infile.replace('.txt','')))
        print '\t',dataname
        savearray = np.column_stack((self._times, self._data[:,1:]))
        np.savetxt(dataname, savearray,fmt='%.3f',delimiter='\t')

# configuration
configname = './config_win.ini'

#read configuration
settings = ConfigParser.ConfigParser()
settings.read(configname)
hvdata = settings.get('settings','kHVdatadir')
hvsave = settings.get('settings','kHVsavedir')

datafiles   = next(os.walk(hvdata))[2]
reportfiles = next(os.walk(hvsave))[2]

# loop over data and find files for which no report is generated yet
for ir in range(len(reportfiles)):
    reportfiles[ir] = reportfiles[ir].replace('.pdf','.txt')
    reportfiles[ir] = reportfiles[ir].replace('Report_HV_','')

print '\nAll datafiles:\n\n', datafiles
print '\nAll reports:\n\n', reportfiles

# find generated
done = list(set(datafiles) & set(reportfiles))
# find data to be processed (ignoring preproduction foils)
process =  [item for item in datafiles if item not in done and not 'PP' in item]

print '\nList to be processed ({})\n\n'.format(len(process))
print process, '\n'


for ifoil in range(len(process)):
    print 'Processing {}/{}:'.format(ifoil+1, len(process))
    mfoil = MFoil(configname, process[ifoil])
    del mfoil
    plt.close("all")


'''
mfoil = MFoil(configname, 'O2-G4-009-20170608-18-50.txt')
del mfoil
'''
#raw_input('Press Enter to exit')
