import socket
import sys
import time
import json
import urllib2
import dsync
from thread import *

IN_PI = True
try:
    # noinspection PyUnresolvedReferences
    import RPi.GPIO as GPIO
except ImportError:
    print("This service is not running on a Raspberry Pi")
    IN_PI = False

HOST = ''
PORT = 8952

SERVICE = 11
DB_WRITE = 12
RX = 13
TX = 15
BLINK = 0.05
RUN = True
SIGNATURE = "D457GHFD347T"

if IN_PI:
    API = "http://127.0.0.1/index.php/AthenaAPI/"
else:
    API = "http://127.0.0.1/athena/index.php/AthenaAPI/"

if IN_PI:
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(SERVICE, GPIO.OUT)
    GPIO.setup(DB_WRITE, GPIO.OUT)
    GPIO.setup(RX, GPIO.OUT)
    GPIO.setup(TX, GPIO.OUT)


def turn_on(pin):
    if IN_PI:
        GPIO.output(pin, GPIO.HIGH)


def turn_off(pin):
    if IN_PI:
        GPIO.output(pin, GPIO.LOW)


def init_pins():
    turn_on(SERVICE)
    time.sleep(BLINK)
    turn_off(SERVICE)
    time.sleep(BLINK)
    turn_on(RX)
    time.sleep(BLINK)
    turn_off(RX)
    time.sleep(BLINK)
    turn_on(TX)
    time.sleep(BLINK)
    turn_off(TX)
    time.sleep(BLINK)
    turn_on(DB_WRITE)
    time.sleep(BLINK)
    turn_off(DB_WRITE)
    time.sleep(BLINK)
    turn_on(SERVICE)


def ci_action(function):
    return urllib2.urlopen(API + function).read()


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
print 'Socket Created'

try:
    s.bind((HOST, PORT))
    init_pins()
except socket.error, msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()

print 'Socket Bound to Port 8952'
s.listen(10)
print 'Socket is Listening...'


def blink_tx():
    start_new_thread(blink, (TX,))


def blink_rx():
    start_new_thread(blink, (RX,))


def blink_db_write():
    start_new_thread(blink, (DB_WRITE,))


def blink(pin):
    if IN_PI:
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(BLINK)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(BLINK)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(BLINK)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(BLINK)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(BLINK)
        GPIO.output(pin, GPIO.LOW)


def stop_service():
    global RUN
    RUN = False


def client_thread(connection, ip, port):
    buff = ''
    used = False
    while True:
        data = connection.recv(1024)
        print ("Received Data: " + data.strip())
        try:
            blink_rx()
            payload = json.loads(data.strip())
            buff = ''
        except ValueError:
            payload = None
            if not data:
                try:
                    blink_rx()
                    payload = json.loads(buff)
                    buff = ''
                except ValueError:
                    if used:
                        print("Connection Closed")
                        sys.exit()
                    else:
                        print("Unknown Protocol")
                        print('Closing connection with ' + str(ip) + ":" + str(port))
                        sys.exit()
            else:
                print("Incoming Data Buffered")
                buff += data.strip()
            print(buff)
        if not payload:
            if len(buff) > 0:
                continue
            if len(data) > 0:
                print("Unknown Protocol")
            else:
                print 'Error Receiving Data'
            print 'Closing connection with ' + str(ip) + ":" + str(port)
            break
        if "ping" in payload['mode'] and "PING Athena" in payload['message']:  # Ping/Discovery Protocol
            blink_rx()
            print("Was just pinged, Responding Back...")
            # TODO: Respond back through the same socket.
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            except socket.error, message:
                print "Failed to create socket.Error code: " + str(message[0]) + ', Error message : ' + message[1]
                sys.exit()
            sock.connect((payload['source'], 8953))
            try:
                response = {'mode': "ping", 'source': payload['destination'],
                            'message': "I'm codeName Athena!", "destination": payload['source']}
                response = json.dumps(response)
                print("Responding with {0}.".format(response))
                blink_tx()
                sock.sendall(json.dumps(response))
                sock.close()
                print("Closing connection with {0}:{1}".format(ip, 8953))
                sys.exit()
            except socket.error:
                print 'Send failed'
                sys.exit()
        if "iModeA" in payload['mode']:  # iModeA Protocol
            blink_rx()
            print("set to initialise android app.")
            errors = {}
            if "handle" in payload['data-type']:
                if "1" in ci_action("verifyHandle/" + payload['data']):
                    try:
                        response = {"mode": "iModeA", "data-type": "verify-packet",
                                    "data": {"flag": "Ok", "signature": SIGNATURE,
                                             "staff": json.loads(ci_action("getStaffInfoByHandle/" + payload[
                                                 'data']))}, "errors": len(errors), "error-codes": errors,
                                    "signature": ""}
                        blink_tx()
                        _json = json.dumps(response)
                        connection.sendall(_json)
                        print("Response: {0}".format(_json))
                        used = True
                        continue
                    except socket.error, message:
                        print "Error Verifying Packet: Code: {0}, Message: {1}".format(message[0], message[1])
                else:
                    if not (len(payload['data']) == 10):
                        errors[str(len(errors))] = "0x001"
                    if "1" in ci_action("verifyHandle/" + payload['data']):
                        errors[str(len(errors))] = "0x002"
                    else:
                        errors[str(len(errors))] = "0x003"
                    try:
                        response = {"mode": "iModeA", "data-type": "verify-packet",
                                    "data": {"flag": "Bad", "signature": "",
                                             "staff": {}}, "errors": len(errors), "error-codes": errors}
                        blink_tx()
                        _json = json.dumps(response)
                        connection.sendall(_json)
                        print("Response: {0}".format(_json))
                        sys.exit()
                    except socket.error, message:
                        print "Error Verifying Packet: Code: {0}, Message: {1}".format(message[0], message[1])
            if "ACK" in payload['data-type']:
                if "verify-packet" in payload['data']['type'] and "nullifyHandle" in payload['data']['r-action']:
                    errors = {}
                    response = json.loads(ci_action("nullifyHandle/" + payload['data']['handle']))
                    if ("1" in response['wipe'] and "1" in response['log']) or "1" in response['wipe']:
                        reply = {"mode": "iModeA", "data-type": "ACK",
                                 "data": {"type": "r-action", "r-action": "", "or-action": "nullifyHandle"},
                                 "errors": len(errors),
                                 "error-codes": errors}
                        blink_tx()
                        reply = json.dumps(reply)
                        print("Responding with: {0}".format(reply))
                        connection.sendall(reply)
                        print("Closing connection with {0}:{1}".format(ip, port))
                        sys.exit()
                    else:
                        if "0" in response['log']:
                            print("Error-0x005")
                        else:
                            print ("Error-0x006")
                            errors[str(len(errors))] = "0x006"
                            reply = {"mode": "iModeA", "data-type": "ACK",
                                     "data": {"type": "r-action", "r-action": "", "or-action": "nullifyHandle"},
                                     "errors": len(errors),
                                     "error-codes": errors}
                            blink_tx()
                            reply = json.dumps(reply)
                            print("Responding with {0}".format(reply))
                            connection.sendall(reply)
                            print("Closing connection with {0}:{1}".format(ip, port))
                            sys.exit()
                else:
                    print("Unknown Protocol")
                    sys.exit()
            else:
                print ("Unknown Protocol")
                sys.exit()
        if "super" in payload['mode']:  # Superuser Protocol
            blink_rx()
            if "nova226" in payload['security']:
                if "shutdown" in payload['action']:
                    stop_service()
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    except socket.error, message:
                        print "Failed to create socket.Error code: " + str(message[0]) + ', Error message : ' + message[
                            1]
                        sys.exit()
                    sock.connect(("127.0.0.1", 8952))
                    try:
                        dud = {'mode': "dud"}
                        sock.sendall(json.dumps(dud))
                        print(json.dumps(dud))
                        sock.close()
                        sys.exit()
                    except socket.error:
                        print 'Send failed'
                        sys.exit()
        if "dud" in payload['mode']:
            sys.exit()
        if "iModeM" in payload['mode']:  # iModeM Protocol.
            blink_rx()
            print ("Module Connected, Chatting has Begun.")
            if "X" in payload['signature']:
                added = 0
                fpmid = ""
                while added == 0:
                    fpmid = ci_action("generateAlphanumeric/12")
                    if "1" in ci_action("addModule/{0}".format(fpmid)):
                        added = 1
                response = {"keepAlive": 0, "mode": "iModeM", "signature": SIGNATURE, "fpmid": fpmid}
                response = json.dumps(response)
                print ("Responding with {0}".format(response))
                blink_tx()
                connection.sendall(response)
            else:
                print("Module Already Initialized with a department")
                response = {"keepAlive": 0, "mode": "iModeM", "signature": "X", "fpmid": "X"}
                response = json.dumps(response)
                print ("Responding with {0}".format(response))
                blink_tx()
                connection.sendall(response)
        if SIGNATURE in payload['signature']:
            blink_rx()
            print("Signature Match!, Processing Request...")
            if "syncA" in payload['mode']:
                blink_rx()
                print ("Synchronization Mode Started...")
                if "1" in ci_action("verifyKey/" + payload['key'] + "/" + str(payload['uid'])):
                    if "download" in payload['type']:
                        print("Sending Data...")
                        errors = {}
                        version = int(ci_action("getVersion/" + payload['table']))
                        if version > payload['version']:
                            table_data = ci_action("getTable/" + payload['table'])
                            if "[]" in table_data:
                                is_empty = 1
                            else:
                                is_empty = 0
                            response = {"mode": "sync", "type": "d-response",
                                        "signature": SIGNATURE,
                                        "conn-stat": 1,
                                        "data": json.loads(table_data),
                                        "is_empty": is_empty,
                                        "should_wipe": 1,
                                        "version": version, "errors": len(errors), "error-codes": errors}
                            print("Flagging that table has been downloaded by user.")
                            if "1" not in (ci_action("flagTaken/" + payload['table'] + "/1")):
                                errors[str(len(errors))] = "0x011"
                            response = json.dumps(response)
                            print("Responding with {0}".format(response))
                            blink_tx()
                            connection.sendall(response)
                            if 0 == payload['conn-stat']:
                                print("Closing connection with {0}:{1}".format(ip, port))
                                sys.exit()
                            if 1 == payload['conn-stat']:
                                print("Continuing Connection")
                                used = True
                                continue
                            else:
                                print("Improper Connection Status")
                                print("Closing connection with {0}:{1}".format(ip, port))
                                sys.exit()
                        else:
                            print(version)
                            print(payload['version'])
                            if version == -1:
                                errors[str(len(errors))] = "0x008"
                            elif version < payload['version']:
                                errors[str(len(errors))] = "0x007"
                            response = {"mode": "sync", "type": "d-response",
                                        "signature": SIGNATURE,
                                        "data": {},
                                        "is_empty": 1,
                                        "should_wipe": 0,
                                        "version": version, "errors": len(errors), "error-codes": errors,
                                        "conn-stat": 1, "key": "", "uid": payload['uid']}
                            response = json.dumps(response)
                            print("Responding with {0}".format(response))
                            blink_tx()
                            connection.sendall(response)
                            if 0 == payload['conn-stat']:
                                print("Closing connection with {0}:{1}".format(ip, port))
                                sys.exit()
                            if 1 == payload['conn-stat']:
                                print("Continuing Connection")
                                used = True
                                continue
                            else:
                                print("Improper Connection Status")
                                print("Closing connection with {0}:{1}".format(ip, port))
                                sys.exit()
                    elif "upload" in payload['type']:
                        print("Getting Data...")
                        commands = payload['data']
                        success = True
                        fails = []
                        position = 0
                        errors = {}
                        for command in commands:
                            print("Executing Command {0} ...".format(command))
                            blink_db_write()
                            code = ci_action("modifyTable/" + dsync.translate(command.strip()))
                            if "1" not in code:
                                success = False
                            if success:
                                print("Command Executed Successfully")
                            else:
                                if "3" in code:
                                    code = "0x013"
                                elif "2" in code:
                                    code = "0x014"
                                else:
                                    code = "0x15"
                                fails.append([position, code])
                                print("Problem Executing Command")
                                success = True
                            position += 1
                        if len(fails) > 0:
                            errors[str(len(errors))] = "0x009"
                        response = {"mode": "sync", "conn-stat": 1, "type": "u-response", "signature": SIGNATURE,
                                    "table": fails, "version": 0, "key": "", "data": "ACK", "uid": 0,
                                    "errors": len(errors), "error-codes": errors}
                        response = json.dumps(response)
                        print("Responding with {0} ...".format(response))
                        blink_tx()
                        connection.sendall(response)
                        if 0 == payload['conn-stat']:
                            print("Synchronization Complete.")
                            print("Closing connection with {0}:{1}".format(ip, port))
                            sys.exit()
                        if 1 == payload['conn-stat']:
                            print("Continuing Connection")
                            used = True
                            continue
                        else:
                            print("Improper Connection Status")
                            print("Closing connection with {0}:{1}".format(ip, port))
                            sys.exit()
                    elif "calibrate" in payload['type']:
                        print("Calibrating...")
                        tables = payload['data']
                        success = True
                        fails = []
                        position = 0
                        errors = {}
                        for table in tables:
                            if "1" not in ci_action("calibrateTable/" + table):
                                success = False
                            if success:
                                print("Table: {0} calibrated successfully.".format(table))
                            else:
                                print("Table: {0} not successfully calibrated".format(table))
                                fails.append(position)
                                success = True
                            position += 1
                        if len(fails) > 0:
                            errors[str(len(errors))] = "0x012"
                        response = {"mode": "sync", "conn-stat": 1, "type": "c-response", "signature": SIGNATURE,
                                    "table": fails, "version": 0, "errors": len(errors), "error-codes": errors,
                                    "key": "", "uid": payload['uid']}
                        response = json.dumps(response)
                        print("Responding with {0} ...".format(response))
                        blink_tx()
                        connection.sendall(response)
                        if 0 == payload['conn-stat']:
                            print("Synchronization Complete.")
                            print("Closing connection with {0}:{1}".format(ip, port))
                            sys.exit()
                        if 1 == payload['conn-stat']:
                            print("Continuing Connection")
                            used = True
                            continue
                        else:
                            print("Improper Connection Status")
                            print("Closing connection with {0}:{1}".format(ip, port))
                            sys.exit()
                else:
                    print ("Error 0x010: Security ID Mismatch")
                    errors = {"0": "0x010"}
                    response = {"mode": "sync", "conn-stat": 0, "type": payload['type'][0:1] + "-response",
                                "signature": SIGNATURE, "table": "", "version": 0, "key": "", "data": "!ACK", "uid": 0,
                                "errors": len(errors), "error-codes": errors}
                    response = json.dumps(response)
                    print("Responding with {0} ...".format(response))
                    blink_tx()
                    connection.sendall(response)
                    print("Closing connection with {0}:{1}".format(ip, port))
                    sys.exit()
            if "passport" in payload['mode']:
                print("Passport Packet Received. Processing...")
                blink_rx()
                if "image" in payload['type']:
                    response = {"mode": "passport", "type": "ack", "signature": SIGNATURE, "data": 1}
                    response = json.dumps(response)
                    print ("Responding with {0}".format(response))
                    blink_tx()
                    connection.sendall(response)
                    time.sleep(0.2)
                    print("Preparing to write passport file...")
                    f = open(payload['data'] + ".jpg", 'wb')
                    print("Receiving Passport...")
                    binaries = connection.recv(1024)
                    while binaries:
                        blink_rx()
                        f.write(binaries)
                        binaries = connection.recv(1024)
                    f.close()
                    print("Done Receiving Passport")
                    print("Done Receiving Passport")
                    print("Closing connection with {0}:{1}".format(ip, port))
                    sys.exit()
                elif "request" in payload['type']:
                    f = open(payload['data'], "rb")
                    print("Sending Passport...")
                    binaries = f.read(1024)
                    while binaries:
                        blink_tx()
                        connection.sendall(binaries)
                        binaries = f.read(1024)
                    f.close()
                    print("Done Sending Passport")
                    print("Done Receiving Passport")
                    print("Closing connection with {0}:{1}".format(ip, port))
                    sys.exit()
            if "syncM" in payload['mode']:  # syncM Protocol
                print("Finger Module Connected and Requesting Synchronization")
                blink_rx()
                if "1" in ci_action("verifyModule/{0}".format(payload['fpmid'])):
                    fpmid = payload['fpmid']
                    if "request" in payload['dataType'] and "necessities" in payload['data']:
                        module_pack = json.loads(ci_action("getModulePack"))
                        students = module_pack["students"]
                        staffs = module_pack['staffs']
                        print("Beginning Synchronization")
                        for record in students:  # Sending Students...
                            packet = {"keepAlive": 1, "mode": "syncM", "signature": SIGNATURE, "fpmid": fpmid,
                                      "dataType": "student", "data": {"sid": record['id'], "fpTemplate": record['hash'],
                                                                      "fpid": record['mid']}}
                            packet = json.dumps(packet)
                            print ("Sending Module Packet: {0}".format(packet))
                            blink_tx()
                            connection.sendall(packet)
                            ack = False
                            while not ack:
                                try:
                                    data = connection.recv(1024)
                                    data = json.loads(data)
                                    ack = True
                                    blink_rx()
                                    if "syncM" in data['mode'] and SIGNATURE in data['signature']:
                                        if fpmid in data['fpmid']:
                                            if "ack" in data['dataType'] and data['data'] == 1:
                                                break
                                            else:
                                                print("Module returned a negative acknowledge packet")
                                                connection.close()
                                                sys.exit()
                                        else:
                                            print ("Invalid Module for session")
                                    else:
                                        print ("Protocol corrupted in session")
                                except ValueError:
                                    ack = False
                        for record in staffs:
                            packet = {"keepAlive": 1, "mode": "syncM", "signature": SIGNATURE, "fpmid": fpmid,
                                      "dataType": "staff", "data": {"sid": record['id'], "fpTemplate": record['hash'],
                                                                    "fpid": record['mid']}}
                            packet = json.dumps(packet)
                            print ("Sending Module Packet: {0}".format(packet))
                            blink_tx()
                            connection.sendall(packet)
                            ack = False
                            while not ack:
                                try:
                                    data = connection.recv(1024)
                                    data = json.loads(data)
                                    ack = True
                                    blink_rx()
                                    if "syncM" in data['mode'] and SIGNATURE in data['signature']:
                                        if fpmid in data['fpmid']:
                                            if "ack" in data['dataType'] and data['data'] == 1:
                                                break
                                            else:
                                                print("Module returned a negative acknowledge packet")
                                                connection.close()
                                                sys.exit()
                                        else:
                                            print ("Invalid Module for session")
                                    else:
                                        print ("Protocol corrupted in session")
                                except ValueError:
                                    ack = False
                        for record in staffs:  # Sending Staffs...
                            packet = {"keepAlive": 1, "mode": "syncM", "signature": SIGNATURE, "fpmid": fpmid,
                                      "dataType": "securityId", "data": record['security_id']}
                            packet = json.dumps(packet)
                            print ("Sending Module Packet: {0}".format(packet))
                            blink_tx()
                            connection.sendall(packet)
                            ack = False
                            while not ack:
                                try:
                                    data = connection.recv(1024)
                                    data = json.loads(data)
                                    ack = True
                                    blink_rx()
                                    if "syncM" in data['mode'] and SIGNATURE in data['signature']:
                                        if fpmid in data['fpmid']:
                                            if "ack" in data['dataType'] and data['data'] == 1:
                                                break
                                            else:
                                                print("Module returned a negative acknowledge packet")
                                                connection.close()
                                                sys.exit()
                                        else:
                                            print ("Invalid Module for session")
                                    else:
                                        print ("Protocol corrupted in session")
                                except ValueError:
                                    ack = False
                        module_name = ci_action("getModuleName/{0}".format(fpmid))  # Sending Module Name...
                        packet = {"keepAlive": 1, "mode": "syncM", "signature": SIGNATURE, "fpmid": fpmid,
                                  "dataType": "moduleName", "data": module_name}
                        packet = json.dumps(packet)
                        print ("Sending Module Packet: {0}".format(packet))
                        connection.sendall(packet)
                        blink_tx()
                        ack = False
                        while not ack:
                            try:
                                data = connection.recv(1024)
                                data = json.loads(data)
                                ack = True
                                blink_rx()
                                if "syncM" in data['mode'] and SIGNATURE in data['signature']:
                                    if fpmid in data['fpmid']:
                                        if "ack" in data['dataType'] and data['data'] == 1:
                                            break
                                        else:
                                            print("Module returned a negative acknowledge packet")
                                            connection.close()
                                            sys.exit()
                                    else:
                                        print ("Invalid Module for session")
                                else:
                                    print ("Protocol corrupted in session")
                            except ValueError:
                                ack = False
                        lecture_hall = ci_action("getLectureHallForModule/{0}".format(fpmid))  # Sending Lecture Hall...
                        packet = {"keepAlive": 1, "mode": "syncM", "signature": SIGNATURE, "fpmid": fpmid,
                                  "dataType": "lectureHall", "data": lecture_hall}
                        packet = json.dumps(packet)
                        print ("Sending Module Packet: {0}".format(packet))
                        connection.sendall(packet)
                        blink_tx()
                        ack = False
                        while not ack:
                            try:
                                data = connection.recv(1024)
                                data = json.loads(data)
                                ack = True
                                blink_rx()
                                if "syncM" in data['mode'] and SIGNATURE in data['signature']:
                                    if fpmid in data['fpmid']:
                                        if "ack" in data['dataType'] and data['data'] == 1:
                                            break
                                        else:
                                            print("Module returned a negative acknowledge packet")
                                            connection.close()
                                            sys.exit()
                                    else:
                                        print ("Invalid Module for session")
                                else:
                                    print ("Protocol corrupted in session")
                            except ValueError:
                                ack = False
                        packet = {"keepAlive": 1, "mode": "syncM", "signature": SIGNATURE, "fpmid": fpmid,
                                  "dataType": "request", "data": "stats"}  # Requesting Stats...
                        packet = json.dumps(packet)
                        print ("Sending Module Packet: {0}".format(packet))
                        connection.sendall(packet)
                        blink_tx()
                        ack = False
                        while not ack:
                            try:
                                data = connection.recv(1024)
                                data = json.loads(data)
                                ack = True
                                blink_rx()
                                if "syncM" in data['mode'] and SIGNATURE in data['signature']:
                                    if fpmid in data['fpmid']:
                                        if "mStats" in data['dataType']:
                                            if "1" in ci_action("logModuleStats/{0}/{1}/{2}".format(fpmid,
                                                                                                    data['data'][
                                                                                                        'nUsed'],
                                                                                                    data['data'][
                                                                                                        'battery'])):
                                                packet = {"keepAlive": 0, "mode": "syncM", "fpmid": fpmid,
                                                          "dataType": "X",
                                                          "data": "X"}
                                                packet = json.dumps(packet)
                                                print ("Sending Module Packet: {0}".format(packet))
                                                connection.sendall(packet)
                                                blink_tx()
                                                print("Module Sync Ended")
                                                print("Closing Connection")
                                                connection.close()
                                                sys.exit()
                                            else:
                                                print("Error in Logging module stats for {0}".format(fpmid))
                                                sys.exit()
                                        else:
                                            print("Module returned a negative acknowledge packet")
                                            connection.close()
                                            sys.exit()
                                    else:
                                        print ("Invalid Module for session")
                                else:
                                    print ("Protocol corrupted in session")
                            except ValueError:
                                ack = False
                else:
                    print ("Unknown Module")
                    print ("Closing Connection")
        else:
            if len(payload['signature']) == 12:
                print("Unknown Signature")
            else:
                print("Unknown Protocol")
            print("Disconnecting with " + str(ip) + ":" + str(port))
            break
    connection.close()


# to ensure server is live
while RUN:
    conn, address = s.accept()
    # display client information
    print 'Connected with ' + address[0] + ':' + str(address[1])
    start_new_thread(client_thread, (conn, address[0], address[1],))

print("Shutdown Signal Received.")
print("Shutting Down Athena...")
s.close()
turn_off(SERVICE)
time.sleep(1.5)
print("Athena has been shutdown.")
