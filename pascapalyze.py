#!/usr/bin/python3 

import sys, os, re
from struct import *
from binascii import *
from itertools import *
from collections import *
from math import *
from zipfile import ZipFile

def grok(fname, size, ark):
    if size == 0:
        return []
    with ark.open(fname, 'r') as src:
        nums = []
        count = 0
        data = src.read(12 * size)
        if not data or len(data) != 12 * size:
            print("Data set did not contain advertised number of elements:", data==None, len(data), 12*size)
            return []
        for k in range(4,12*size,12):
            nums.append(unpack("d",data[k:k+8])[0])
        return [nums]

def transpose(arr):
    if not arr:
        return []
    c = max(len(a) for a in arr)
    ext = [list(a) + [0]*(c - len(a)) for a in arr]
    return list(zip(*ext))

def mumpf(doubles):
    tdoubles = transpose(doubles)
    return "".join(str(line[0]) + "\t" + str(line[1]) + "\n" for line in tdoubles)

def segment(text, string):
    idcs = [-1]
    while True:
        i = text.find(string, idcs[-1]+1)
        idcs.append(i)
        if i == -1:
            break
    return [text[i:j] for i,j in zip(idcs[1:],idcs[2:])]


matcherDep = re.compile("<DependentStorageElement [^>]*FileName=\"([^\"]+)\"")
matcherIndep = re.compile("<IndependentStorageElement [^>]*FileName=\"([^\"]+)\"")
matcherTS = re.compile("<IndependentStorageElement [^>]*IntervalCacheInterval=\"([^\"]+)\"")
matcherNumber = re.compile("DataGroupNumber=\"([^\"]+)\"")
matcherSize = re.compile("DataCacheDataSize=\"([^\"]+)\"")
def grab_sets(text):
    dep = list(re.findall(matcherDep, text))
    indep = list(re.findall(matcherIndep, text))
    group = list(re.findall(matcherNumber, text))
    ts = list(re.findall(matcherTS, text))
    s = list(re.findall(matcherSize,text))
    if len(s) > 1 and s[0] != s[1]:
        print("Warning: size mismatch")
    if dep and indep and group and s:
        return int(group[0]), indep[0], dep[0], int(s[0])
    if dep and ts and group and s:
        return int(group[0]), float(ts[0]), dep[0], int(s[0])
    print("could not parse: dep,indep,ts,group,s = ",dep,indep,ts,group,s)
    return None,None,None,None

def diff(x):
    return map(lambda g: g[1]-g[0], zip(x,x[1:]))

matchDataType = re.compile("MeasurementName=\"([^\"]+)\"")
matchDataChannel = re.compile(" ChannelIDName=\"([^\"]+)\"")# space before disambiguates
matchSetNo = re.compile("ZTDDRBPUsageName=\"[^\"#]*#([0-9]*)[^\"]*\"")
matchResult = re.compile("ZCFDICurveFitParameterResultValue=\"([^\"]+)\"")

def process(ark, dirn):
    text = str(ark.read("main.xml"))
    data = defaultdict(dict)
    for seg in segment(text, "<DataSource "):
        label = list(re.findall(matchDataType, seg))
        if not label:
            continue
        lblstr = label[0]
        channel = list(re.findall(matchDataChannel, seg))
        if channel:
            lblstr += "-" + channel[0]
        for subseg in segment(seg, "<DataSet"):
            number, x, y, s = grab_sets(subseg)
            print(number,x,y,s,label)
            if number is None:
                continue
            data[number][lblstr] = (x,y,s)

    # curve fit parameters (let's not trust these completely)
    fits = {}
    for seg in segment(text, "<ZRSIndividualRenederer"):
        name = list(re.findall(matchSetNo, seg))
        segments = segment(seg, "<ZCFDICurveFitParameterDefinition")
        if len(segments) != 2:
            continue
        segi, segs = segments
        slp = list(re.findall(matchResult, segs))
        intsc = list(re.findall(matchResult, segi))
        if name and slp and intsc:
            fits[int(name[0])] = (float(intsc[0]),float(slp[0]))

    if not os.path.exists(dirn+"/"):
        os.mkdir(dirn+"/")
    for number, val in sorted(list(data.items()), key=lambda x:x[0]):
        text = "# dump from cap file\n@WITH G0\n@G0 ON\n"
        i = 0
        for label, (x,y,s) in sorted(list(val.items()),key=lambda x:x[0]):
            if s == 0:# no data for set
                continue
            print("Processing:", number,i,label)
            prefix = "# %d, field \"%s\", from %s and %s.\n@TYPE xy\n@    legend string %d \"%s\"\n" % (number,label,str(x),y,i,label)
            i += 1
            if type(x) == float:
                dep = grok(y,s, ark)
                if not dep:
                    continue
                indep = [[x*i for i in range(len(dep[0]))]]
                things = indep + dep
            else:
                things = grok(x,s,ark) + grok(y,s,ark)
            if not things:
                print("failed to read:",i,x,y,s,number)
                continue
            body = mumpf(things)
            text += (prefix + body + "&\n")
        open(dirn+"/set"+str(number)+".txt", "w").write(text);


if __name__ == "__main__":
    indexfile = sys.argv[1]
    ark = ZipFile(indexfile, 'r')
    dirn = ".".join(indexfile.split(".")[:-1])
    process(ark, dirn)