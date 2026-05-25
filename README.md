# Check TrueNAS - JSON-RPC 2.0 over WebSocket API
This is a Nagios/Icinga check plugin using the TrueNAS "JSON-RPC 2.0 over WebSocket" API to check for Alerts, Pool health, Pool capacity, Replication errors and TrueNAS software updates (update check requires TrueNAS 25.10+). I forked this from Stewart Loving-Gibbard (https://github.com/StewLG/check_truenas_extended_play) because TrueNAS will stop supporting the legacy REST API starting with version 26. 

I have tested this with two TrueNAS 25.10.2 Systems and one TrueNAS 26.0.0-BETA.1 System. There are might still be egde-cases where this script does not work.  
Feel free to open an issue for bugs, improvements or feature requests.

# Overview
```
usage: check_truenas_jsonrpc.py [-h] -H HOSTNAME [-u USER] -p PASSWD -t TYPE [-pn ZPOOLNAME] [-n NAME] [-ns] [-nv] [-ig] [-d] [-zw ZPOOL_WARN] [-zc ZPOOL_CRITICAL] [-zp] [-w WARN] [-c CRIT] [-pd]

Checks a TrueNAS server using the JSON-RPC 2.0 over WebSocket API. Version 2.2

options:
  -h, --help            show this help message and exit
  -H, --hostname HOSTNAME
                        Hostname or IP address
  -u, --user USER       Username, if not specified: use API Key
  -p, --passwd PASSWD   Password or API Key
  -t, --type TYPE       Type of check, either alerts, zpool, zpool_capacity, repl, update, or disk_temps
  -pn, --zpoolname ZPOOLNAME
                        For compatibility with older version of this plugin. Same as --name.
  -n, --name NAME       Resource name (e.g. disk name, pool name). Optional.
  -ns, --no-ssl         Disable SSL (use WS); default is to use SSL (use WSS)
  -nv, --no-verify-cert
                        Do not verify the server SSL cert; default is to verify the SSL cert
  -ig, --ignore-dismissed-alerts
                        Ignore alerts that have already been dismissed in FreeNas/TrueNAS; default is to treat them as relevant
  -d, --debug           Display debugging information; run script this way and record result when asking for help.
  -zw, --zpool-warn ZPOOL_WARN
                        For compatibility with older version of this plugin. Same as --warn.
  -zc, --zpool-critical ZPOOL_CRITICAL
                        For compatibility with older version of this plugin. Same as --crit.
  -zp, --zpool-perfdata
                        For compatibility with older version of this plugin. Same as --perfdata.
  -w, --warn WARN       Warning threshold (Integer). Optional.
  -c, --crit CRIT       Critical threshold (Integer). Optional.
  -pd, --perfdata       Add perf data to output. Optional.

```
# Requirements

- Python 3.10 or greater
- python3-websockets

# Authentication
I recommend setting up a read-only user for monitoring with the following privileges:

- Readonly Admin
- Alert Read
- Dataset Read
- Pool Read
- Replication Task Read
- Reporting Read
- System Update Read

Using an API Key is preferred, however TrueNAS afaik does not allow the use of API Keys without SSL. If for some reason you can't use SSL, authenticate with user and password.

# Version History

*17.06.2026 - Version 2.0*

Forked from https://github.com/StewLG/check_truenas_extended_play and updated to use the TrueNAS "JSON-RPC 2.0 over WebSocket" API.

*20.06.2026 - Version 2.1*

Added support for API query filters and options. Reworked check_zpool_capacity to use API query filters and options.

*24.06.2026 - Version 2.2*

Added more general --warn, --crit, --name and --perfdata flags while keeping compatibility with the old --zpool-warn, --zpool-critical, --zpoolname and --zpool-perfdata flags.
With "check_disk_temps" @MisterMountain added the first non-zpool check that use those flags. 
