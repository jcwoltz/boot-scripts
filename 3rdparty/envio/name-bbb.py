#!/usr/bin/env python

#import eeprom as bb
try:
    import paho.mqtt.publish as publish
    import netifaces
    import socket
    from datetime import datetime
    import os
    import json
except ImportError, e:
    print "Missing Module. Error: {}".format(e)

def getBBBmfid(verbose=False):
    i2cfile = None
    if os.path.isfile("/sys/bus/i2c/devices/0-0050/eeprom"):
        i2cfile = "/sys/bus/i2c/devices/0-0050/eeprom"
    elif os.path.isfile("/sys/bus/i2c/devices/1-0050/eeprom"):
        i2cfile = "/sys/bus/i2c/devices/1-0050/eeprom"
    elif os.path.isfile("/sys/bus/i2c/devices/2-0050/eeprom"):
        i2cfile = "/sys/bus/i2c/devices/2-0050/eeprom"
    else:
        return None
    try:
        with open(i2cfile) as fin:
            fin.seek(4)
            board = fin.read(8)
            if str(board) == "A335BNLT":
                boardver = fin.read(4)
                boardsn = fin.read(12)
            else:
                print "EEprom contains {} Expected {}".format(board,"A335BNLT")
        if verbose:
            print board
            print boardver
            print boardsn
        ebsn = "{0}{1}".format(boardsn[:4], boardsn[8:])
        sndecoded = "year 20{0} week {1} boardnum {2}".format(boardsn[2:4], boardsn[0:2], boardsn[8:])
        mfid = {'boardver': boardver, 'boardsn': boardsn, 'ebsn': ebsn, 'friendly': sndecoded}
        return mfid
    except (IOError, ValueError):
        return None


def setBBBHostname(set_minion_id=False):
    try:
        mfid = getBBBmfid()
    except Exception, e:
        print("unknown error: {}".format(e))
        return
    if mfid is None:
        return "Error"
    boardver = formatBBBver(mfid['boardver'])
    if boardver is 'unknownbv':
        boardver = "u"
        print "Unknown board version: " + mfid['boardver']
    bsn = mfid['ebsn']
    hostname = "envio-GW-{}-{}".format(boardver, bsn)
    with open('/etc/hostname', 'w') as f:
        f.write(hostname)
        f.write('\n')
    if set_minion_id:
        if os.path.isfile("/etc/salt/minion_id"):
            with open('/etc/salt/minion_id', 'w') as f:
                f.write(hostname)
        else:
            print "Error: minion_id file does not exist"
    return hostname


def formatBBBver(ver="0"):
    """
    Lookup Table to format version string. 4 byte str input
    :param ver:
    :return:
    info https://github.com/beagleboard/image-builder/blob/master/readme.md
    """
    return {
        '000C': 'C',
        '000B': 'B',
        '00A6': 'A6',
        '0A5A': 'A5a',
        '0A5B': 'A5b',
        '0A5C': 'A5c',
        '\x1a\x00\x00\x00': 'ssgreen',  # SeedStudio BB Green
        'AIA0': 'aarowi',  # ArrowBeagleBone Black Industrial
        'EIA0': 'e14i',  # Element14 BeagleBone Black Industrial
        'SE0A': 'sancloud',  # SanCloud BeagleBone Enhanced
        '\x74\x0a\x75\x65': 'embest',  # Embest replica?
        'GH01': 'ghi'       # GHI OSD3358 Dev Board
    }.get(ver, 'unknownbv')


def getBBBSerial():
    try:
        mfid = getBBBmfid()
    except Exception, e:
        print("unknown error: {}".format(e))
        return None
    return mfid['boardsn']


def getnetiface():
    nics = netifaces.interfaces()
    gws = netifaces.gateways()
    ip_addresses = {}
    jtest = {}
    print gws
    print nics
    print ""
    hostname = socket.gethostname()
    jtest['hostname'] = hostname
    if gws['default'].has_key(netifaces.AF_INET):
        default_nic_name = gws['default'][netifaces.AF_INET][1]
        addrs = netifaces.ifaddresses(default_nic_name)
        if len(addrs[netifaces.AF_LINK]) == 1 and (addrs[netifaces.AF_LINK][0].has_key('addr')):
            default_nic_mac = addrs[netifaces.AF_LINK][0]['addr']
            jtest['INET'] = {'name': default_nic_name, 'mac': default_nic_mac, 'other': addrs}
        else:
            print("unknown error")

    if gws['default'].has_key(netifaces.AF_INET6):
        default_nic6_name = gws['default'][netifaces.AF_INET6][1]
        addrs = netifaces.ifaddresses(default_nic6_name)
        if len(addrs[netifaces.AF_LINK]) == 1 and (addrs[netifaces.AF_LINK][0].has_key('addr')):
            default_nic6_mac = addrs[netifaces.AF_LINK][0]['addr']
            jtest['INET6'] = {'name': default_nic6_name, 'mac': default_nic6_mac, 'other': addrs}
        else:
            print("unknown error")
    jtest['whenprocessed'] = datetime.utcnow().isoformat()
    return jtest


def main():
    global hostname
    run = True
    jt = None
    setBBBHostname(True)
    mfid = getBBBmfid()
    print(mfid)
    with open('/etc/hostname', 'r') as f:
        hostname = f.read()

    try:
        jt = getnetiface()
    except:
        print "unable to get netifaces"
    if jt is not None:
        print publish.single("test/" + hostname + "/network/info/prepBBB", payload=json.dumps(jt),
                             hostname="inf.mq.envio.systems", qos=2, retain=True)


if __name__ == '__main__':
    main()
