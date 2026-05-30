#!/usr/bin/env python3

# The MIT License (MIT)
# Copyright (c) 2015 Goran Tornqvist
# Extended by Stewart Loving-Gibbard 2020, 2021, 2022, 2023
# Additional help from Folke Ashberg 2021
# Updated by Steffen Zimmermann 2026
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys

# Attempt to require minimum version of Python
#
# NOTE: This will NOT work much of the time, and instead you'll get a cryptic 
# error because this script won't compile at all in earlier versions of Python.
#
# For example, several users are seeing this and not understanding it:
#
# curie# ./check_truenas_extended_play.py
#  File "./check_truenas_extended_play.py", line 48
#    ZpoolName: str
#
# This is dying because of the user of Dataclass in earlier versions of Python that
# don't recognize it. Dataclass was introduced in Python 3.7.
# 
# So, this is both the least and most we can do without having wrappers or shell scripts
# or batch files, none of which is going to make this script any easier to use.
#
# Sorry I can't do more without deliberately avoding language features!
#
# -- SLG 3/1/2022
#
# Bumped minimum required Python version to 3.10, because websockets requires it.
#
# -- Steffen 20.05.2026
MIN_PYTHON = (3, 10)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

import json
import ssl
import argparse
import logging
import time
from websockets.sync.client import connect
from dataclasses import dataclass

@dataclass
class ZpoolCapacity:
    ZpoolName: str
    ZpoolAvailableBytes: int
    TotalUsedBytesForAllDatasets: int
  

class Startup(object):

    def __init__(self, hostname, user, secret, use_ssl, verify_cert, ignore_dismissed_alerts, debug_logging, zpool_name, zpool_warn, zpool_crit, show_zpool_perfdata, name, warn, crit, show_perfdata):
        self._hostname = hostname
        self._user = user
        self._secret = secret
        self._use_ssl = use_ssl
        self._verify_cert = verify_cert
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._ignore_dismissed_alerts = ignore_dismissed_alerts
        self._debug_logging = debug_logging
        if (zpool_name != "all"):
            self._name = zpool_name
        else:
            self._name = name
        if (zpool_warn):
            self._warn = zpool_warn
        else:
            self._warn = warn
        if (zpool_crit):
            self._crit = zpool_crit
        else:
            self._crit = crit
        if (show_zpool_perfdata):
            self._perfdata = show_zpool_perfdata
        else:
            self._perfdata = show_perfdata
 
        ws_request_header = 'wss' if use_ssl else 'ws'
 
        self._base_url = ('%s://%s/api/current' % (ws_request_header, hostname) )
        
        self.setup_logging()
        self.log_startup_information()

        if (self._verify_cert == False):
            self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE

        if (self._use_ssl == False):
            self._ws = connect(self._base_url)
        else:
            self._ws = connect(self._base_url, ssl=self._ssl_context)      

    def log_startup_information(self):
        logging.debug('')
        logging.debug('hostname: %s', self._hostname)
        logging.debug('use_ssl: %s', self._use_ssl)
        logging.debug('verify_cert: %s', self._verify_cert)
        logging.debug('base_url: %s', self._base_url)
        logging.debug('name: %s', self._name)
        logging.debug('warn: %d', self._warn)
        logging.debug('crit: %d', self._crit)
        logging.debug('')
 
    def do_request(self, resource, options):
        try:
            request_url = self._base_url
            logging.debug('request_url: %s', request_url)

            if (self._user):
                self._ws.send(json.dumps({
                    'jsonrpc': '2.0',
                    'method': 'auth.login',
                    'params': [self._user, self._secret],
                    'id': 1
                }))
            else:
                self._ws.send(json.dumps({
                    'jsonrpc': '2.0',
                    'method': 'auth.login_with_api_key',
                    'params': [self._secret],
                    'id': 1
                }))
            self._ws.recv()

            if (options == None):
                payload=(json.dumps({
                'jsonrpc': '2.0',
                'method': resource,
                'params': [],
                'id': 1
            }))
            else:
                payload=(json.dumps({
                    'jsonrpc': '2.0',
                    'method': resource,
                    'params': options,
                    'id': 1
                }))
            #print(f"{payload}")
            self._ws.send(payload)
            r = json.loads(self._ws.recv())
            #print(f"{r}")
            return r.get("result")
        except:
            print ('UNKNOWN - request failed - Error when contacting TrueNAS server: ' + str(sys.exc_info()) )
            sys.exit(3)
 
        #if r.ok:
        try:
            return r.get("result")
        except:
            print ('UNKNOWN - json failed to parse - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)

    def check_repl(self):
        repls = self.do_request('replication.query', None)
        errors=0
        msg=''
        replications_examined = ''

        try:
            for repl in repls:
                logging.debug('Replication response: %s', repl)
                repl_name = repl['name']
                logging.debug('Replication name: %s', repl_name)
                repl_state_obj = repl['state']
                logging.debug('Replication state object: %s', repl_state_obj)
                repl_state_code = repl_state_obj['state']
                logging.debug('Replication state code: %s', repl_state_code)

                replications_examined = replications_examined + ' ' + repl_name + ': ' + repl_state_code
                
                repl_was_not_success = (repl_state_code != 'FINISHED')
                repl_not_running = (repl_state_code != 'RUNNING')
                if (repl_was_not_success and repl_not_running):
                    errors = errors + 1
                    msg = msg + repl_name + ': ' + repl_state_code
        except:
            print ('UNKNOWN - check_repl() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)
 
        if errors > 0:
            print ('WARNING - There are ' + str(errors) + ' replication errors [' + msg.strip() + ']. Go to Storage > Replication Tasks > View Replication Tasks in TrueNAS for more details.')
            sys.exit(1)
        else:
            print ('OK - No replication errors. Replications examined: ' + replications_examined)
            sys.exit(0)

    def check_update(self):
        updateCheckResult = self.do_request('update.status', None)
        warnings=0
        errors=0
        msg=''
        needsUpdateOrOtherPossibleIssue=False
        updateCheckResultVersion=''
        updateCheckResultDownloadStatus=''
        updateMissionCritical=False
        
        try:
            logging.debug('Update check result: %s', updateCheckResult)
            if (updateCheckResult['code'] == "NORMAL"):
                try: 
                    updateCheckResultVersion = updateCheckResult['status']['new_version']['version']
                    updateCheckResultDownloadStatus = updateCheckResult['update_download_progress']['description']
                    needsUpdateOrOtherPossibleIssue = True
                except: 
                    needsUpdateOrOtherPossibleIssue = False
            elif (updateCheckResult['code'] == "ERROR"):
                needsUpdateOrOtherPossibleIssue = True

        except:
            print ('UNKNOWN - check_update() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)
 
        if (needsUpdateOrOtherPossibleIssue):

            if (updateCheckResultVersion):
                print ('WARNING - Update to Version ' + updateCheckResultVersion + ' available. ' +updateCheckResultDownloadStatus)
            # Unfamiliar status we've never seen before    
            else:
                print ('WARNING - Unknown Update Status: ' + updateCheckResultString + '. Update may be required. Go to TrueNAS Dashboard -> System -> Update to check for newer version.')
            sys.exit(1)
        else:
            print ('OK - No update available.')
            sys.exit(0)

    def check_alerts(self):
        alerts = self.do_request('alert.list', None)
        
        logging.debug('alerts: %s', alerts)
        
        warn=0
        crit=0
        critical_messages = ''
        warning_messages = ''
        try:
            for alert in alerts:
                # Skip over dismissed alerts if that's what user requested 
                if (self._ignore_dismissed_alerts and alert['dismissed'] == True):
                    continue
                if alert['level'] == 'CRITICAL':
                    crit = crit + 1
                    critical_messages = critical_messages + '- (C) ' + alert['formatted'].replace('\n', '. ') + ' '
                elif alert['level'] == 'WARNING':
                    warn = warn + 1
                    warning_messages = warning_messages + '- (W) ' + alert['formatted'].replace('\n', '. ') + ' '
        except:
            print ('UNKNOWN - check_alerts() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)
        
        if crit > 0:
            # Show critical errors before any warnings
            print ('CRITICAL ' + critical_messages + warning_messages)
            sys.exit(2)
        elif warn > 0:
            print ('WARNING ' + warning_messages)
            sys.exit(1)
        else:
            print ('OK - No problem alerts')
            sys.exit(0)
            
    def check_disk_temps(self):
        temperatures = self.do_request('disk.temperatures', None)

        if (self._warn == None):
            self._warn = 45
        if (self._crit == None):
            self._crit = 55

        warn_threshold = self._warn
        crit_threshold = self._crit

        warn = 0
        crit = 0
        critical_messages = ''
        warning_messages = ''
        disks_examined = ''
        perfdata = ''
        if (self._perfdata):
            perfdata= ' |'

        all_disk_names = ''
        actual_disk_count = 0

        all_disks = self._name.lower() == 'all'

        try:
            for disk_name in sorted(temperatures.keys()):
                actual_disk_count += 1
                all_disk_names += disk_name + ' '

                if not all_disks and disk_name != self._name:
                    continue

                temp = temperatures[disk_name]
                logging.debug('Disk %s temperature: %s', disk_name, temp)
                if temp is None:
                    if all_disks:
                        continue
                    crit += 1
                    critical_messages += '- (C) ' + disk_name + ': no temperature reading '
                    continue
                temp_display = f'{temp:.2f}' if isinstance(temp, float) else str(temp)
                disks_examined += ' ' + disk_name + ': ' + temp_display + 'C'
                if self._perfdata:
                    perfdata += ' ' + disk_name + '=' + temp_display + 'C;' + str(warn_threshold) + ';' + str(crit_threshold) + ';0;100'
                if temp >= crit_threshold:
                    crit += 1
                    critical_messages += '- (C) ' + disk_name + ': ' + temp_display + 'C '
                elif temp >= warn_threshold:
                    warn += 1
                    warning_messages += '- (W) ' + disk_name + ': ' + temp_display + 'C '
        except:
            print ('UNKNOWN - check_disk_temps() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)

        if disks_examined == '' and not all_disks and crit == 0 and warn == 0:
            crit += 1
            if actual_disk_count > 0:
                critical_messages = '- No disk found matching {} out of {} disks ({})'.format(self._name, actual_disk_count, all_disk_names.strip())
            else:
                critical_messages = '- No disk found matching {} (no disks reported by server)'.format(self._name)

        if(disks_examined == ''):
            print ('UNKNOWN - check_disk_temps() - No temperatures received.')
            sys.exit(3)
        elif crit > 0:
            print ('CRITICAL ' + critical_messages + warning_messages + disks_examined + perfdata)
            sys.exit(2)
        elif warn > 0:
            print ('WARNING ' + warning_messages + disks_examined + perfdata)
            sys.exit(1)
        else:
            print ('OK - No disk temperature issues. Disks examined:' + disks_examined + perfdata)
            sys.exit(0)

    def check_zpool(self):
        pool_results = self.do_request('pool.query', None)

        #logging.debug('pool_results: %s', pool_results)
        
        warn=0
        crit=0
        critical_messages = ''
        warning_messages = ''
        zpools_examined = ''
        actual_zpool_count = 0
        all_pool_names = ''
        
        looking_for_all_pools = self._name.lower() == 'all'
        
        try:
            for pool in pool_results:

                actual_zpool_count += 1
                pool_name = pool['name']
                pool_status = pool['status']
                
                all_pool_names += pool_name + ' '
                
                logging.debug('Checking zpool for relevancy: %s with status %s', pool_name, pool_status)
                
                # Either match all pools, or only the requested pool
                if (looking_for_all_pools or self._name == pool_name):
                    logging.debug('Relevant Zpool found: %s with status %s', pool_name, pool_status)
                    zpools_examined = zpools_examined + ' ' + pool_name
                    logging.debug('zpools_examined: %s', zpools_examined)
                    if (pool_status != 'ONLINE'):
                        crit = crit + 1
                        critical_messages = critical_messages + '- (C) ZPool ' + pool_name + 'is ' + pool_status
        except:
            print ('UNKNOWN - check_zpool() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)
        
        # There were no Zpools on the system, and we were looking for all of them
        if (zpools_examined == '' and actual_zpool_count == 0 and looking_for_all_pools):
            zpools_examined = '(None - No Zpools found)'
            
        # There were no Zpools matching a specific name on the system
        if (zpools_examined == '' and actual_zpool_count > 0 and not looking_for_all_pools and crit == 0):
            crit = crit + 1
            critical_messages = '- No Zpools found matching {} out of {} pools ({})'.format(self._name, actual_zpool_count, all_pool_names)

        if crit > 0:
            # Show critical errors before any warnings
            print ('CRITICAL ' + critical_messages + warning_messages)
            sys.exit(2)
        elif warn > 0:
            print ('WARNING ' + warning_messages)
            sys.exit(1)
        else:
            print ('OK - No problem Zpools. Zpools examined: ' + zpools_examined)
            sys.exit(0)
  
    def check_zpool_capacity(self):

        BYTES_IN_MEGABYTE = 1024 * 1024;

        logging.debug('check_zpool_capacity')
        
        if (self._warn == None):
            self._warn = 80
        if (self._crit == None):
            self._crit = 90
        
        warnZpoolCapacityPercent = self._warn
        critZpoolCapacityPercent = self._crit
        
        warn=0
        crit=0
        critical_messages = ''
        warning_messages = ''
        zpools_examined_with_no_issues = ''
        root_level_datasets_examined = ''
        root_level_dataset_count = 0
        all_root_level_dataset_names = ''
        perfdata = ''
        if (self._perfdata):
            perfdata= ' |'

        # We allow filtering on pool name here
        looking_for_all_pools = self._name.lower() == 'all'

        # Build a dict / array thingy and add to it as we proceed...
        zpoolNameToCapacityDict = {}

        queryOptions = (
            [['name', '=', self._name.lower()]],
            {
            'extra': {
                'flat': False,
                'properties': ["type", "used", "available"],
                'retrieve_children': False
                }
            }
        )

        if (looking_for_all_pools):
          queryOptions = (
            [],
            {
            'extra': {
                'flat': False,
                'properties': ["type", "used", "available"],
                'retrieve_children': False
                }
            }
        )

        dataset_results = self.do_request('pool.dataset.query', queryOptions)           

        try:
            for dataset in dataset_results:
                root_level_dataset_count += 1
                dataset_name = dataset['name']
                dataset_pool_name = dataset['pool']

                all_root_level_dataset_names += dataset_name + ' '

                logging.debug('Checking root-level dataset for relevancy: dataset %s from pool %s', dataset_name, dataset_pool_name)
                
                logging.debug('Relevant root-level dataset found: dataset %s from pool %s', dataset_name, dataset_pool_name)
                root_level_datasets_examined = root_level_datasets_examined + ' ' + dataset_name
                logging.debug('root_level_datasets_examined: %s', root_level_datasets_examined)

                dataset_used_bytes = dataset['used']['parsed']
                dataset_available_bytes = dataset['available']['parsed']

                logging.debug('dataset_used_bytes: %d', dataset_used_bytes)
                logging.debug('dataset_available_bytes: %d', dataset_available_bytes)

                newZpoolCapacity = ZpoolCapacity(dataset_pool_name, dataset_available_bytes, dataset_used_bytes)
                zpoolNameToCapacityDict[dataset_pool_name] = newZpoolCapacity

                logging.debug('currentZpoolCapacity: ' + str(zpoolNameToCapacityDict[dataset_pool_name]))

                for currentZpoolCapacity in zpoolNameToCapacityDict.values():
                    zpoolTotalBytes = currentZpoolCapacity.ZpoolAvailableBytes + currentZpoolCapacity.TotalUsedBytesForAllDatasets
                    usedPercentage = (currentZpoolCapacity.TotalUsedBytesForAllDatasets / zpoolTotalBytes ) * 100;
                    usagePercentDisplayString = f'{usedPercentage:3.1f}'

                    logging.debug('Warning capacity: ' + str(warnZpoolCapacityPercent) + '%' + ' Critical capacity: ' + str(critZpoolCapacityPercent) + '%')                 
                    logging.debug('ZPool ' + str(currentZpoolCapacity.ZpoolName) + ' usedPercentage: ' + usagePercentDisplayString + '%')  

                    # Add warning/critical errors for the current ZPool summary being checked, if needed
                    if (usedPercentage >= critZpoolCapacityPercent):
                        crit += 1
                        critical_messages += " - Pool " + currentZpoolCapacity.ZpoolName + " usage " + usagePercentDisplayString + "% exceeds critical value of " + str(critZpoolCapacityPercent) + "%"                        
                    elif (usedPercentage >= warnZpoolCapacityPercent):
                        warn += 1
                        warning_messages += " - Pool " + currentZpoolCapacity.ZpoolName + " usage " + usagePercentDisplayString + "% exceeds warning value of " + str(warnZpoolCapacityPercent) + "%"
                    else:
                        # Don't add dashes to start, only to additions
                        if (len(zpools_examined_with_no_issues) > 0):
                            zpools_examined_with_no_issues += ' - '
                        zpools_examined_with_no_issues += currentZpoolCapacity.ZpoolName + ' (' + usagePercentDisplayString + '% used)'                    

                    # Add perfdata if user requested it
                    if (self._perfdata):
                        usedMegaBytes = currentZpoolCapacity.TotalUsedBytesForAllDatasets / BYTES_IN_MEGABYTE
                        usedMegabytesString = f'{usedMegaBytes:3.2f}'                    

                        warningBytes = zpoolTotalBytes * (warnZpoolCapacityPercent / 100)
                        warningMegabytes = warningBytes / BYTES_IN_MEGABYTE
                        warningMegabytesString = f'{warningMegabytes:3.2f}'

                        criticalBytes = zpoolTotalBytes * (critZpoolCapacityPercent / 100)
                        criticalMegabytes = criticalBytes / BYTES_IN_MEGABYTE
                        criticalMegabytesString = f'{criticalMegabytes:3.2f}'

                        totalMegabytes = zpoolTotalBytes / BYTES_IN_MEGABYTE
                        totalMegabytesString = f'{totalMegabytes:3.2f}' 

                        logging.debug('usedMegabytesString: ' + usedMegabytesString)  
                        logging.debug('warningMegabytesString: ' + warningMegabytesString)  
                        logging.debug('criticalMegabytesString: ' + criticalMegabytesString)                      
                        logging.debug('totalMegabytesString: ' + totalMegabytesString)  

                        perfdata += " " + currentZpoolCapacity.ZpoolName + "=" + usedMegabytesString + "MB;" + warningMegabytesString + ";" + criticalMegabytesString + ";0;" + totalMegabytesString                                

        except:
            print ('UNKNOWN - check_zpool() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)

        # There were no datasets on the system, and we were looking for datasets from any pool
        if (root_level_datasets_examined == '' and root_level_dataset_count == 0 and looking_for_all_pools):
            root_level_datasets_examined = '(No Datasets found)'
            
        # There were no datasets matching the requested specific pool name on the system
        if (root_level_datasets_examined == '' and root_level_dataset_count > 0 and not looking_for_all_pools and crit == 0):
            crit = crit + 1
            critical_messages = '- No datasets found matching ZPool {} out of {} root level datasets ({})'.format(self._name, root_level_dataset_count, all_root_level_dataset_names)

        # If we have zpools with no issues to show in a warning/error, we want a leading dash in front of it.
        # Otherwise, no dash.
        error_or_warning_dividing_dash = ''
        if (len(zpools_examined_with_no_issues) > 0):
            error_or_warning_dividing_dash = ' - '
            logging.debug('Yes there is a dividing dash:' + error_or_warning_dividing_dash)

        if crit > 0:
            # Show critical errors before any warnings
            print ('CRITICAL' + critical_messages + warning_messages + error_or_warning_dividing_dash + zpools_examined_with_no_issues + perfdata)
            sys.exit(2)
        elif warn > 0:
            print ('WARNING' + warning_messages + error_or_warning_dividing_dash + zpools_examined_with_no_issues + perfdata)
            sys.exit(1)
        else:
            print ('OK - No Zpool capacity issues. ZPools examined: ' + zpools_examined_with_no_issues + ' - Root level datasets examined:' + root_level_datasets_examined + perfdata)
            sys.exit(0)

    def check_cpu_temps(self):

        logging.debug('check_cpu_temps')
        
        if (self._warn == None):
            self._warn = 80
        if (self._crit == None):
            self._crit = 90
        
        warn_threshold = self._warn
        crit_threshold = self._crit
        
        warn=0
        crit=0
        critical_messages = ''
        warning_messages = ''
        cpus_examined_with_no_issues = ''
        cpus_examined = ''
        cpu_count = 0
        all_cpu_names = ''
        perfdata = ''
        if (self._perfdata):
            perfdata= '|'

        all_cpus = self._name.lower() == 'all'

        #We query for all cpus since TrueNAS seems to ignore the identifier for this query.
        queryOptions = (
            [
                [{'name': 'cputemp', 'identifier': None}],
                {'aggregate': True, 'start': int(time.time()-5)}
            ]
        )
        temperatures = self.do_request('reporting.get_data', queryOptions)

        try:
            for cpu_name in temperatures[0]['aggregations']['mean']:
                all_cpu_names += cpu_name + ' '
                if not all_cpus and cpu_name != self._name:
                    continue
                
                try:
                    temp = temperatures[0]['aggregations']['mean'][cpu_name]
                except:
                    print ('UNKNOWN - check_cpu_temps() - No temperatures received: ' + str(sys.exc_info()))
                    sys.exit(3)
                logging.debug('CPU %s temperature: %s', cpu_name, temp)
                if temp is None:
                    if all_cpus:
                        continue
                    crit += 1
                    critical_messages += '- (C) ' + cpu_name + ': no temperature reading '
                    continue
                temp_display = f'{temp:.2f}' if isinstance(temp, float) else str(temp)
                cpus_examined += ' ' + cpu_name + ': ' + temp_display + 'C'
                if self._perfdata:
                    perfdata += ' ' + cpu_name + '=' + temp_display + 'C;' + str(warn_threshold) + ';' + str(crit_threshold) + ';0;100'
                if temp >= crit_threshold:
                    crit += 1
                    critical_messages += '- (C) ' + cpu_name + ': ' + temp_display + 'C '
                elif temp >= warn_threshold:
                    warn += 1
                    warning_messages += '- (W) ' + cpu_name + ': ' + temp_display + 'C '
        except:
            print ('UNKNOWN - check_cpu_temps() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)

        if cpus_examined == '' and not all_cpus and crit == 0 and warn == 0:
            crit += 1
            if actual_disk_count > 0:
                critical_messages = '- No CPU found matching {} out of {} CPUs ({})'.format(self._name, cpu_count, all_cpu_names.strip())
            else:
                critical_messages = '- No CPU found matching {} (no CPUs reported by server)'.format(self._name)

        if(cpus_examined == ''):
            print ('UNKNOWN - check_cpu_temps() - No temperatures received.')
            sys.exit(3)
        if crit > 0:
            print ('CRITICAL ' + critical_messages + warning_messages + cpus_examined + perfdata)
            sys.exit(2)
        elif warn > 0:
            print ('WARNING ' + warning_messages + cpus_examined + perfdata)
            sys.exit(1)
        else:
            print ('OK - No CPU temperature issues. CPUs examined:' + cpus_examined + perfdata)
            sys.exit(0)

    def check_load(self):

        logging.debug('check_load')
        
        if (self._warn == None):
            self._warn = 5
        if (self._crit == None):
            self._crit = 10
        
        warn_threshold = self._warn
        crit_threshold = self._crit
        
        warn=0
        crit=0
        critical_messages = ''
        warning_messages = ''
        perfdata = ''
        if (self._perfdata):
            perfdata= ' |'

        queryOptions = (
            [
                [{'name': 'load', 'identifier': None}],
                {'aggregate': True, 'start': int(time.time()-15)}
            ]
        )
        load = self.do_request('reporting.get_data', queryOptions)

        try:

            shortterm_display = f'{load[0]['aggregations']['max']['shortterm']:.2f}'
            midterm_display = f'{load[0]['aggregations']['max']['midterm']:.2f}'
            longterm_display = f'{load[0]['aggregations']['max']['longterm']:.2f}'

            if self._perfdata:
                perfdata += ' load1=' + shortterm_display + ';' + str(warn_threshold) + ';' + str(crit_threshold) + ';0;'
                perfdata += ' load5=' + midterm_display + ';' + str(warn_threshold) + ';' + str(crit_threshold) + ';0;'
                perfdata += ' load15=' + longterm_display + ';' + str(warn_threshold) + ';' + str(crit_threshold) + ';0;'

            if (load[0]['aggregations']['max']['shortterm'] > crit_threshold):
                crit += 1
                critical_messages += '- (C) load1: ' + shortterm_display
            elif (load[0]['aggregations']['max']['shortterm'] > warn_threshold):
                warn += 1
                warning_messages += '- (W) load1: ' + shortterm_display
            if (load[0]['aggregations']['max']['midterm'] > crit_threshold):
                crit += 1
                critical_messages += '- (C) load5: ' + midterm_display
            elif (load[0]['aggregations']['max']['midterm'] > warn_threshold):
                warn += 1
                warning_messages += '- (W) load5: ' + midterm_display
            if (load[0]['aggregations']['max']['longterm'] > crit_threshold):
                crit += 1
                critical_messages += '- (C) load15: ' + longterm_display
            elif (load[0]['aggregations']['max']['longterm'] > warn_threshold):
                warn += 1
                warning_messages += '- (W) load15: ' + longterm_display

        except:
            print ('UNKNOWN - check_load() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)

        if crit > 0:
            print ('CRITICAL ' + critical_messages + perfdata)
            sys.exit(2)
        elif warn > 0:
            print ('WARNING ' + warning_messages + perfdata)
            sys.exit(1)
        else:
            print ('OK - No load issues.' + perfdata)
            sys.exit(0)

    def check_memory(self):

        # This memory check might not be the most accurate. I've tried to calculate the used memory by subtracting
        # available memory and memory used for ZFS caching (ARC) from the total amount of memory. 

        logging.debug('check_memory')

        if (self._warn == None):
            self._warn = 80
        if (self._crit == None):
            self._crit = 90
        
        warn_threshold = self._warn
        crit_threshold = self._crit
        
        warn=0
        crit=0
        critical_messages = ''
        warning_messages = ''
        perfdata = ''
        if (self._perfdata):
            perfdata= ' |'

        queryOptions1 = (
            [
                [{'name': 'memory', 'identifier': None}],
                {'aggregate': True, 'start': int(time.time()-15)}
            ]
        )

        queryOptions2 = (
            [
                [{'name': 'arcsize', 'identifier': None}],
                {'aggregate': True, 'start': int(time.time()-15)}
            ]
        )

        try:
            # We need to query the target twice for memory, because reporting.get_data only returns used memory and 
            # not total and/or used.
            # We also need to query it once more for the ZFS cache size, since the ZFS cache is not included in
            # available memory even though it is technically available. 
            free_memory = self.do_request('reporting.get_data', queryOptions1)
            zfs_cache = self.do_request('reporting.get_data', queryOptions2)
            total_memory = self.do_request('system.info', None)

            used_memory = (total_memory['physmem'] - free_memory[0]['aggregations']['min']['available'] - zfs_cache[0]['aggregations']['min']['size'])
            used_memory_percent = (used_memory / total_memory['physmem'] * 100)
            used_memory_percent_display = f'{used_memory_percent:.2f}'
            if (self._perfdata):
                perfdata += ' memory=' + used_memory_percent_display + ';' + str(warn_threshold) + ';' + str(crit_threshold) + ';0;100'

        except:
            print ('UNKNOWN - check_memory() - Error when contacting TrueNAS server: ' + str(sys.exc_info()))
            sys.exit(3)    

        if (used_memory_percent > crit_threshold):
            critical_messages = '- (C) Memory useage is ' + used_memory_percent_display + '%'
            print ('CRITICAL ' + critical_messages + perfdata)
            sys.exit(2)
        elif (used_memory_percent > warn_threshold):
            warning_messages = '- (W) Memory useage is ' + used_memory_percent_display + '%'
            print ('WARNING ' + warning_messages + perfdata)
            sys.exit(1)   
        else:
            print ('OK - No memory issues.' + perfdata)
            sys.exit(0)
     

    def handle_requested_alert_type(self, alert_type):
        if alert_type == 'alerts':
            self.check_alerts()
        elif alert_type == 'repl':
            self.check_repl()
        elif alert_type == 'update':
            self.check_update()
        elif alert_type == 'zpool':
            self.check_zpool()
        elif alert_type == 'zpool_capacity':
            self.check_zpool_capacity()
        elif alert_type == 'disk_temps':
            self.check_disk_temps()
        elif alert_type == 'cpu_temps':
            self.check_cpu_temps()
        elif alert_type == 'load':
            self.check_load()
        elif alert_type == 'memory':
            self.check_memory()
        else:
            print ("Unknown type: " + alert_type)
            sys.exit(3)

    def setup_logging(self):
        logger = logging.getLogger()
        
        if (self._debug_logging):
            #print('Trying to set logging level debug')
            logger.setLevel(logging.DEBUG)
        else:
            #print('Should be setting no logging level at all')
            logger.setLevel(logging.CRITICAL)

check_truenas_script_version = '2.3'

def main():
    # Build parser for arguments
    parser = argparse.ArgumentParser(description='Checks a TrueNAS server using the JSON-RPC 2.0 over WebSocket API. Version ' + check_truenas_script_version)
    parser.add_argument('-H', '--hostname', required=True, type=str, help='Hostname or IP address')
    parser.add_argument('-u', '--user', required=False, type=str, help='Username, if not specified: use API Key')
    parser.add_argument('-p', '--passwd', required=True, type=str, help='Password or API Key')
    parser.add_argument('-t', '--type', required=True, type=str, help='Type of check, either alerts, zpool, zpool_capacity, repl, update, disk_temps, cpu_temps, load, memory')
    parser.add_argument('-pn', '--zpoolname', required=False, type=str, default='all', help='For compatibility with older version of this plugin. Same as --name.')
    parser.add_argument('-n', '--name', required=False, type=str, default='all', help='Resource name (e.g. disk name, pool name). Optional.')
    parser.add_argument('-ns', '--no-ssl', required=False, action='store_true', help='Disable SSL (use WS); default is to use SSL (use WSS)')
    parser.add_argument('-nv', '--no-verify-cert', required=False, action='store_true', help='Do not verify the server SSL cert; default is to verify the SSL cert')
    parser.add_argument('-ig', '--ignore-dismissed-alerts', required=False, action='store_true', help='Ignore alerts that have already been dismissed in FreeNas/TrueNAS; default is to treat them as relevant')
    parser.add_argument('-d', '--debug', required=False, action='store_true', help='Display debugging information; run script this way and record result when asking for help.')
    parser.add_argument('-zw', '--zpool-warn', required=False, type=int, help='For compatibility with older version of this plugin. Same as --warn.')    
    parser.add_argument('-zc', '--zpool-critical', required=False, type=int, help='For compatibility with older version of this plugin. Same as --crit.')
    parser.add_argument('-zp', '--zpool-perfdata', required=False, action='store_true', help='For compatibility with older version of this plugin. Same as --perfdata.')
    parser.add_argument('-w', '--warn', required=False, type=int, help='Warning threshold (Integer). Optional.')
    parser.add_argument('-c', '--crit', required=False, type=int, help='Critical threshold (Integer). Optional.')
    parser.add_argument('-pd', '--perfdata', required=False, action='store_true', help='Add perf data to output. Optional.')

    # if no arguments, print out help
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)
 
    # Parse the arguments
    args = parser.parse_args(sys.argv[1:])

    use_ssl = not args.no_ssl
    verify_ssl_cert = not args.no_verify_cert

    startup = Startup(args.hostname, args.user, args.passwd, use_ssl, verify_ssl_cert, args.ignore_dismissed_alerts, args.debug, args.zpoolname, args.zpool_warn, args.zpool_critical, args.zpool_perfdata, args.name, args.warn, args.crit, args.perfdata)
 
    startup.handle_requested_alert_type(args.type)
 
if __name__ == '__main__':
    main()
