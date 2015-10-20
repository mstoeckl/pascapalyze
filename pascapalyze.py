#!/usr/bin/python3 

import sys, os, re
from struct import *
from binascii import *
from itertools import *
from collections import *
from math import *
from scipy import stats

def grok(fname):
    with open(fname, 'rb') as src:
    #data = open(fname, 'rb').read()
        nums = []
        count = 0
        data = src.read1(12)
        while data:
            x = unpack("d",data[4:12])[0]
            if x == 0:
                count += 1
            else:
                count = 0
            nums.append(x)
            if count == 10:
                break
            data = src.read1(12)
        return [nums[:-10]]

def transpose(arr):
    if not arr:
        return []
    c = max(len(a) for a in arr)
    ext = [list(a) + [0]*(c - len(a)) for a in arr]
    return list(zip(*ext))

def loadsets(target1,target2):
    return grok(target1) + grok(target2)

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
def grab_sets(text):
    dep = list(re.findall(matcherDep, text))
    indep = list(re.findall(matcherIndep, text))
    group = list(re.findall(matcherNumber, text))
    ts = list(re.findall(matcherTS, text))
    if dep and indep and group:
        return int(group[0]), indep[0], dep[0]
    if dep and ts and group:
        return int(group[0]), float(ts[0]), dep[0]
    return None,None,None

def diff(x):
    return map(lambda g: g[1]-g[0], zip(x,x[1:]))

matchDataType = re.compile("MeasurementName=\"([^\"]+)\"")
matchSetNo = re.compile("ZTDDRBPUsageName=\"[^\"#]*#([0-9]*)[^\"]*\"")
matchResult = re.compile("ZCFDICurveFitParameterResultValue=\"([^\"]+)\"")
def process(text):
    data = defaultdict(dict)
    for seg in segment(text, "<DataSource "):
        label = list(re.findall(matchDataType, seg))
        if not label:
            continue
        for subseg in segment(seg, "<DataSet"):
            number, x, y = grab_sets(subseg)
            if number is None:
                continue
            data[number][label[0]] = (x,y)

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

    for number, val in sorted(list(data.items()), key=lambda x:x[0]):
        text = "# dump from cap file\n@WITH G0\n@G0 ON\n"
        for i, ( label, (x,y)) in enumerate(sorted(list(val.items()),key=lambda x:x[0])):
            print("Processing:", number,i,label)
            prefix = "# %d, field \"%s\", from %s and %s.\n@TYPE xy\n@    legend string %d \"%s\"\n" % (number,label,str(x),y,i,label)
            if type(x) == float:
                dep = grok(y)
                if not dep:
                    continue
                indep = [[x*i for i in range(len(dep[0]))]]
                things = indep + dep
            else:
                things = loadsets(x,y)
            if not things:
                continue
            body = mumpf(things)
            text += (prefix + body + "&\n")
        open("out/set"+str(number)+".txt", "w").write(text);


if __name__ == "__main__":
    indexfile = sys.argv[1]
    text = open(indexfile,'r').read()
    import cProfile
    cProfile.run("process(text)", "restats")
    import pstats
    p = pstats.Stats('restats')
    p.strip_dirs().sort_stats("cumulative").print_stats()