#!/usr/bin/env python3

import signal
import sys, os
from sys import argv
import socket

import traceback

from time import gmtime, strftime, sleep

import bluepy.btle as btle
import mysql.connector

# Define signal handler to catch SIGINT event
def signal_handler_sigint(sig, frame):
    now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    print(now, "Catched SIGINT, exiting now.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler_sigint)
#signal.pause()

class Config:
    def __init__(self, configfilename):
        self.configfilename = configfilename
        self.host = None
        self.port = None
        self.database = None
        self.user = None
        self.password = None
        self.configdic = {'host': 'localhost',
                'port': 3306,
                'database': 'btradar',
                'user': 'btradar',
                'password': 'secret'}
        self.config_read()
        self.set_configattributs()

    def config_read(self):
        configlist = []
        try:
            with open(self.configfilename, "r") as configfile:
                for line in configfile:
                    if line[0] != '#' and line[0] != '\n':
                        configlist.append(line.strip('\n').split('='))
        except (IndexError, FileNotFoundError):
            print("\nCall: {} <conffile>".format(__file__))
            exit()

        for configitem in configlist:
            if configitem[0] in self.configdic.keys():
                self.configdic[configitem[0]] = configitem[1].strip('"')
            else:
                print('Unknown configitemn: ', configitem[0])

    def show(self):
        print('Current config:')
        for configitem in self.configdic.keys():
            print("{:30} {}".format(configitem, self.configdic[configitem]))

    def set_configattributs(self):
        for key, value in self.configdic.items():
            setattr(self, key, value)
        self.port = int(self.port)

class Dbase:
    def __init__(self, configdata):
        self.config = configdata

    def _connect(self):
        try:
            self.connection = mysql.connector.connect(host=config.host,
                    port=config.port,
                    user=config.user,
                    password=config.password,
                    database=config.database)
        except:
            print('connection error. Please check config (username, password etc.)')
            exit()

        self.cursor = self.connection.cursor()

    def execute_sql(self, sql, arguments=None):
        self._connect()
        self.cursor.execute(sql, arguments)
        data = self.cursor.fetchone()
        self.connection.commit()
        self._disconnect()
        return data

    def _disconnect(self):
        self.connection.close()

class ScanDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        if isNewDev:
            print(now, "Discovered device", dev.addr)
            db.execute_sql('insert ignore into devices (addr, addrType, name, connectable) values (%s,%s,%s,%s)', (dev.addr, dev.addrType[:1], dev.getValueText(9), dev.connectable))
            db.execute_sql('insert ignore into seen (addr, time, rssi, seenby) values (%s,%s,%s,%s)', (dev.addr, now, dev.rssi, thishost))
            for (adtype, descr, value) in dev.getScanData():
                db.execute_sql('insert ignore into scandata (addr, adtype, descr, value) values (%s,%s,%s,%s)', (dev.addr, adtype, descr, value))
        elif isNewData:
            print(now, "Received new data from", dev.addr)
            db.execute_sql('update devices set addrType=%s, name=%s, connectable=%s where addr=%s', (dev.addrType[:1], dev.getValueText(9), dev.connectable, dev.addr))
            db.execute_sql('insert ignore into seen (addr, time, rssi, seenby) values (%s,%s,%s,%s)', (dev.addr, now, dev.rssi, thishost))
            for (adtype, descr, value) in dev.getScanData():
                db.execute_sql('insert ignore into scandata (addr, adtype, descr, value) values (%s,%s,%s,%s)', (dev.addr, adtype, descr, value))

config = Config(argv[1])
db = Dbase(config)

thishost = socket.gethostname()

def main():
    scanner = btle.Scanner().withDelegate(ScanDelegate())
    while True:
        try:
            devices = scanner.scan(60)
            # Wait a short time before start the next scan
            #sleep(1)
            continue
        except btle.BTLEDisconnectError as error:
            now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            print(now, "Bluetooth error occured:", error)
            # Wait a second to ensure things settle
            sleep(1)
            # Now, resume
            pass
        except Exception as error:
            now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            print(now, "Unknown errror occured:", error)
            print(traceback.format_exc())
            sys.exit(1)

if __name__ == '__main__':
    main()

