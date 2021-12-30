'''
todo:
- add filter to find timestamps of interest and only plot those (df=df['sampleTimeStamp.seconds']>Time of interest)
    - Possibly load only timestamps, look for time stamp of interest and get df.index.start (or df.index[0]), then load all data from this index using skiprows
     df = pandas.read_csv(file_path_n, delimiter = ';', usecols = ['sampleTimeStamp.seconds'])
     df2 = pandas.read_csv(file_path_n, delimiter = ';', usecols = ['sampleTimeStamp.seconds','azimuth'], dtype={'azimuth': 'uint16'})
     df2 = df2[(df2['sampleTimeStamp.seconds']>ToI)&&df2['azimuth']==0] to get
     - do the same for the conti radar

done :
- find start of first frame or azimuth = 0. Use skiprows=d, insert entire chunks into RCS and plot complete azimuth rotations instead of each range sweep individually

- also read conti radar data and plot together
    - use threading and check time stamps? plot in parallel
    - possibly plot navico data, find corresponding conti frame (lookup time stamp) and add to plot

'''
from base64 import b64decode
import matplotlib.pyplot as plt #from matplotlib.pyplot import *
import matplotlib.patches as patches
import numpy as np
import pandas # could dask be faster? how does it work?
import time
import json
from pathlib import Path

# possibly use argin instead of dialog box
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()

THIS_DIR = Path(__file__).parent.resolve()

file_path_n = filedialog.askopenfilename(initialdir=THIS_DIR, title="Select a navico radar file", filetypes=(("CSV Files", "*RadarDetectionReading*.csv"),))

file_path_c =filedialog.askopenfilename(initialdir=THIS_DIR, title="Select a Conti (ARS300) radar file", filetypes=(("CSV Files", "*Raw*.csv"),))

global qp, sp, heading, frameTime
heading = 55 # insert heading of landkrabban

#todo add long-lat position and overlay map of local area around sensors
def updateSimrad(RCS,frameTime):
    global cax
    for c in cax.collections:
        c.remove() # need to remove all old contours separately for some reason. otherwise will run out of memory
    cax = ax.contourf(theta, r, RCS, nlevels, cmap='Blues',zorder=0, alpha=0.2)
    plt.title(str(time.gmtime(int(frameTime))))
    plt.pause(0.01)
    
def updateConti(frame):
    global qp, sp, heading
    dist = []
    ang = []
    vrel = []
    RCS2 = []
        
    for tar in frame:
        dist_temp = tar.get('Tar_Dist')
        dist.append(dist_temp)
        ang_temp = -tar.get('Tar_Ang')+heading
        ang.append(ang_temp)
        vrel_temp = tar.get('Tar_Vrel')
        vrel.append(vrel_temp)
        RCS_temp = tar.get('Tar_RCSValue')
        RCS2.append(RCS_temp)
    
    angRad = np.divide(ang,180/np.pi)
    u = np.multiply(vrel,np.sin(angRad))
    v = np.multiply(vrel,np.cos(angRad))
    qp.remove()
    sp.remove()
    qp = ax.quiver(angRad,dist,u,v,RCS2, angles = 'uv', cmap='Reds', clim = (-50, 52.3), scale_units = 'y', scale = 2, width = 0.005)
    sp = ax.scatter(angRad,dist, c=RCS2, cmap='Reds', vmin = -50, vmax = 52.3)
    plt.pause(0.01)
    
df_conti = pandas.read_csv(file_path_c, delimiter = ';', chunksize = 1, usecols = ['sampleTimeStamp.seconds','sampleTimeStamp.microseconds','data'],dtype={'sampleTimeStamp.microseconds' : 'uint32','data' : 'string'})
    
df = pandas.read_csv(file_path_n, delimiter = ';', chunksize = 1, usecols = ['azimuth','range','sampleTimeStamp.seconds','sampleTimeStamp.microseconds'],dtype={'azimuth': 'uint16', 'range': 'float16','sampleTimeStamp.microseconds' : 'uint32'}) #
firstLine = df.get_chunk()
frameTime = firstLine['sampleTimeStamp.seconds']+firstLine['sampleTimeStamp.microseconds']*10**-6
startAzimuth = int(firstLine['azimuth'])
skipRows= int((4094-startAzimuth)/2+1)
radarRange = float(firstLine['range'])
nlevels = 256
azimuth =  np.linspace(0,4094,2048) # numbers found from inspecting csv
r = np.linspace(0,radarRange,512)
partial = int(512/8) # only use the first quarter of the range to save memory and speed up plotting
r = r[0:partial]
theta = azimuth*2*np.pi/4094 + heading*np.pi/180
r, theta = np.meshgrid(r, theta)
RCS = np.zeros(np.shape(r))
fig, ax = plt.subplots(subplot_kw=dict(projection='polar'))
plt.title(str(int(frameTime)))
cax = ax.contourf(theta, r, RCS, nlevels, cmap='Blues',zorder=0, alpha=0.2) # ,alpha=0.5 could be useful for overlay with map
qp = ax.quiver(0,0,0,0,0, angles = 'uv',cmap='Reds', clim = (-50, 52.3), scale_units = 'y', scale = 2, width = 0.005)
sp = ax.scatter(0,0)
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
ax.set_ylim([0,1500/8]) # do we need to se farther than this
# ax.set_thetamin(heading-90)
# ax.set_thetamax(heading+90)
ax.set_thetamin(-20)
ax.set_thetamax(200)
plt.bar(heading*np.pi/180,200, width=17*np.pi/180, bottom=0.0, color="g", alpha=0.2)
plt.bar(heading*np.pi/180,50, width=56*np.pi/180, bottom=0.0, color="y", alpha=0.2)
plt.ion()
plt.show()

# contiThreadHandle = threading.Thread(target=contiThread, args=(radarFrames,))    
# contiThreadHandle.start()

contiFrame = df_conti.get_chunk()
frameTime_c = float(contiFrame['sampleTimeStamp.seconds']+contiFrame['sampleTimeStamp.microseconds']*10**-6)
contiData64 = contiFrame['data']
dictStr = b64decode(contiData64[contiData64.index.start])
for chunk in pandas.read_csv(file_path_n, delimiter = ';', chunksize = 2048, skiprows=[i for i in range(1,skipRows+1)], usecols = ['azimuth','data','sampleTimeStamp.seconds','sampleTimeStamp.microseconds'],dtype={'azimuth': 'uint16', 'data': 'string','sampleTimeStamp.microseconds' : 'uint32'}):
    for row in range(chunk.index.start, chunk.index.stop):
        azm=int(int(chunk.at[row,'azimuth'])/2)
        data64 = chunk.at[row,'data']
        dataStr = list(b64decode(data64))
        dataStr = dataStr[0:partial]
        RCS[:][azm] = dataStr
    frameTime = chunk.at[row,'sampleTimeStamp.seconds']+chunk.at[row,'sampleTimeStamp.microseconds']*10**-6
    updateSimrad(RCS,frameTime)
    # updateConti(json.loads(dictStr).get('targets'))
    while frameTime_c<frameTime:
        contiFrame = df_conti.get_chunk()
        frameTime_c = float(contiFrame['sampleTimeStamp.seconds']+contiFrame['sampleTimeStamp.microseconds']*10**-6)
        # updateConti(contiFrame.get('targets'))
    contiData64 = contiFrame['data']
    dictStr = b64decode(contiData64[contiData64.index.start])
    updateConti(json.loads(dictStr).get('targets')) #plot all or only the latest?
    