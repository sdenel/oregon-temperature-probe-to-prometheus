#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import re
import json
import logging
import urllib.request

log = logging.getLogger("webserver-logger")

# 127.0.0.1 to allow only local usages
# 0.0.0.0 to allow other computers in your network to access the service
ADDRESS = "0.0.0.0"
PORT = 9192
DOMOTICZ_URL = "http://localhost:8088/json.htm?" \
               "type=devices&filter=all&used=true&order=Name&type=temp"

_underscorer1 = re.compile(r'(.)([A-Z][a-z]+)')
_underscorer2 = re.compile('([a-z0-9])([A-Z])')


def name_to_prefix(s):
    """
    >>> name_to_prefix("My own probe")
    'my_own_probe'
    >>> name_to_prefix("MyOwnProbe")
    'my_own_probe'
    >>> name_to_prefix("My Own Probe")
    'my_own_probe'
    """
    s_no_space = s.replace(" ", "_")
    subbed = _underscorer1.sub(r'\1_\2', s_no_space)
    c = _underscorer2.sub(r'\1_\2', subbed).lower()
    s_no_redundant_underscore = c.replace("__", "_")
    return s_no_redundant_underscore


def json_to_prometheus(measures_in_json):
    """
    >>> json = {'title': 'Devices', 'result': [
    ... {'TypeImg': 'temperature', 'AddjMulti2': 1.0, 'Unit': 1,
    ... 'CustomImage': 0, 'Used': 1, 'Data': '26.5 C',
    ... 'AddjMulti': 1.0, 'HaveTimeout': False,
    ... 'ShowNotifications': True, 'SignalLevel': 7,
    ... 'Name': 'My beautiful probe', 'BatteryLevel': 100, 'Favorite': 0,
    ... 'AddjValue2': 0.0, 'Type': 'Temp', 'PlanIDs': [0], 'HardwareID': 2,
    ... 'HardwareName': 'RFXCom', 'YOffset': '0',
    ... 'LastUpdate': '2018-07-16 19:40:15', 'XOffset': '0',
    ... 'SubType': 'THC238/268, THN132, THWR288, THRN122, THN122, AW129/131',
    ... 'HardwareType': 'RFXCOM - RFXtrx433 USB 433.92MHz Transceiver',
    ... 'HardwareTypeVal': 1, 'Description': '', 'Protected': False,
    ... 'idx': '1',
    ... 'AddjValue': 0.0, 'PlanID': '0', 'ID': '4901', 'Temp': 26.5,
    ... 'Timers': 'false', 'Notifications': 'false'}],
    ... 'ActTime': 1531770021, 'status': 'OK', 'app_version': '4.9700'}
    >>> print(json_to_prometheus(json))
    # HELP
    # TYPE my_beautiful_probe_temperature gauge
    my_beautiful_probe_temperature 26.5
    # HELP
    # TYPE my_beautiful_probe_battery_level gauge
    my_beautiful_probe_battery_level 100.0
    """
    prometheus_str_as_list = []
    results = measures_in_json['result']
    for r in results:
        prefix = name_to_prefix(r['Name']) + '_'
        prometheus_str_as_list.extend([
            "# HELP",
            "# TYPE " + prefix + "temperature gauge",
            prefix + "temperature " + str(r['Temp'])
        ])
        if 'BatteryLevel' in r:
            prometheus_str_as_list.extend([
                "# HELP",
                "# TYPE " + prefix + "battery_level gauge",
                prefix + "battery_level " + str(1.0 * r['BatteryLevel'])
            ])
    return "\n".join(prometheus_str_as_list)


def get_measures():
    urllib.request.urlopen(DOMOTICZ_URL)
    measures_json_as_str = urllib.request.urlopen(DOMOTICZ_URL).read().decode('utf8')
    measures_json = json.loads(measures_json_as_str)
    return json_to_prometheus(measures_json)


class SimpleHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            measures = get_measures()
            # Send response status code
            self.send_response(200)

            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            self.wfile.write(
                bytes(measures, "utf8")
            )
        except IOError as e:
            logging.error(e)
            self.send_response(500)

            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            self.wfile.write(bytes(str(e), "utf8"))
        return


if __name__ == '__main__':
    log.setLevel(logging.NOTSET)
    logging.basicConfig(
        format="%(levelname)s\t%(message)s",
        level=logging.NOTSET
    )
    log.info(
        'Checking the probe once before starting the webserver: ' +
        get_measures()
    )
    log.info('Starting webserver on ' + ADDRESS + ':' + str(PORT))
    server_address = (ADDRESS, PORT)
    httpd = HTTPServer(server_address, SimpleHttpHandler)
    httpd.serve_forever()
