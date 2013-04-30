# Program to take WICCI csv files downloaded from the USGS-CIDA Geo Data Portal and convert to PRMS format
# Performs same task as John Walker's program wicci_to_cbh, but for GDP output generated by pyGDP, which is seperated into seperate csv files for each Time Period-GCM-Scenario-Variable combination (as opposed to the web GDP interface, which produces lumped files for each time period).

import os
import numpy as np

csvdir='outfiles' # directory containing downloaded files from wicci
cbhdir='cbh' # directory for converted files

print "Getting list of csv files..."
try:
    allfiles=os.listdir(csvdir)
except OSError:
    print "can't find directory with GDP files"
    
csvs = dict()
cind=-1
for cf in allfiles:
    if cf.lower().endswith('.csv'):
        cind = cind+1
        csvs[cind]=cf

print "Converting files to cbh format..."

for file in csvs.itervalues():
    
    print(file),
    
    # get file info
    csvpath=os.path.join(csvdir,file)
    f=open(csvpath,'r')
    name=f.readline()
    values=f.readline()
    parline=f.readline()
    t=False
    p=False    
    if "MEAN(mm)" in parline:
        p=True
        par='prcp'
    elif "MEAN(C)" in parline:
        t=True
        if 'tmin' in file:
            par='tmin'
        elif 'tmax' in file:
            par='tmax'
    else:
        raise Exception("Error: unrecognized parameter!")

    data=np.genfromtxt(csvpath,dtype=None,skiprows=3,delimiter=',')
    num_attribs=len(data[0])-1
    
    # open output file and write headers
    outpath=os.path.join(cbhdir,file[:-4])
    ofp=open(outpath+'.prms','w')
    ofp.write('created by pyGDP_to_cbh.py\r\n')
    ofp.write(par+'      '+str(num_attribs)+'\r\n')
    ofp.write('#'*40+'\r\n')
    
    print('...\t\t'),
    # loop through lines in input file, converting and writing to output, line by line
    for line in data:
        line=list(line)
        # explode date
        datetime=line[0]
        (year,month,day)=datetime[:10].split('-')
        (h,m,s)=datetime[11:-1].split(':')
        
        newline=map(int,[year,month,day,h,m,s])
        
        # convert units
        for value in line[1:]:
            if p:
                if value<=5e-5:
                    valueIn="{0:.4f}".format(0)
                else:
                    valueIn="{0:.4f}".format(value/25.4) # mm/in
            elif t:
                valueIn="{0:.4f}".format(value*(9.0/5.0)+32.0) # C to F
            newline.append(valueIn)
        
        newline=' '.join(map(str,newline)) + '\r\n'
        ofp.write(newline)
    ofp.close()
    print "Done"
print "All files converted!"
    