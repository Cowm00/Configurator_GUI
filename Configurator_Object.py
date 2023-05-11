# -*- coding: utf-8 -*-
# Written by Rune Johannesen, (c)2021-2023
from concurrent.futures import ThreadPoolExecutor
from asyncio import set_event_loop, set_event_loop_policy, wait_for, create_task, sleep, get_event_loop, as_completed, Queue, TimeoutError
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from random import uniform
from operator import attrgetter
from socket import socket, gethostbyname_ex, AF_INET, SOCK_STREAM
from asyncssh import connect, scp, SSHClientConnectionOptions
from asyncssh.misc import PermissionDenied
from logging import Logger, handlers, Formatter, getLogger, INFO
from os import mkdir, getcwd, chdir
from os.path import splitext, basename, dirname, join, exists, realpath
from sys import exit, executable, version_info, platform
import sys
"""
-----------
How to use:
-----------
    from Configurator_Object import Configurator

    async def main():
        Config = Configurator("username", "password")
            NOTE: Configurator variables
            CLI_USER:                   TACACS Username for CLI access (REQUIRED)
            CLI_PASS:                   TACACS Password for CLI access (REQUIRED)
            CLI_ENABLE:                 Enable Password for CLI enable mode access (OPTIONAL) Default: ""
            CONTROLCHAR:                List of characters to look for in the terminal window to determine, when the switch is ready for next command (OPTIONAL)
                                        Default: ["#"] - If you CLI to a Cisco ASA, the control character ">" should be added, e.g.: ["#", ">"]
            COMMANDTIMEOUT:             Time to wait for the device to respond after executing a command. The script will look for the CONTROLCHAR while waiting.
                                        If the CONTROLCHAR is not found within the COMMANDTIMEOUT, the script will raise a timeout exception.
                                        Default: 15 seconds
            COMMANDSLEEP:               Time to wait after writing a command and pressing enter. Default: 0.300 seconds (300 ms).
            MAX_DEVICE_CONNECTIONS:     Maximum parallel connections allowed in the queue. Be carefull what you change here.
                                        Default: 6 connections
            LOGIN_TIMEOUT:              Maximum time to wait for the device to respond to the script trying to login. If the device does not respond within the
                                        time set, the script will raise a timeout exception.
                                        Default: 30 seconds
        << InitiateExecution >>
            Two valid formats:
            1. Same command(s) for all device(s).
                results = await Config.InitiateExecution([["192.168.209.6"], ["Next IP address"]], ["terminal length 0", "show run", "Next command"])
            2. Individual commands per device.
                results = await Config.InitiateExecution([["192.168.209.6", ["terminal length 0", "show run"]], ["Next IP address", ["Commands"]]])
            print(results)
                Returns:
                    Results:
                        [[ipaddress, hostname, [if applicable: list of all responses from each command]]]
                        [['192.168.209.6', 'SDN-LAB-TEST-SW01', ['show run\nBuilding configuration......TRUNCATED']]]
                    NOTE:   Only commands with device response will be returned. Configuration commands etc. will not return any data.
                            In the above example "terminal length 0" is not returned.
                    Errors:
                        [[ipaddress, hostname, [listoferrors]]]
                        [['192.168.1.1', "SDN-LAB-TEST-SW01", ['Device: 192.168.1.1 Error: Invalid input detected: sh hello-test [ SKIPPED ]']]]
                        hostname might return "Not Available" if an error occurs before a connection is made.
                [] (empty list) is returned when connectivity fails for all device(s).
        << InitiateScpTransfer >>
            Use this to transfer large configurations directly to the local storage on a device.
            Afterwards, you can use the above function to copy the configuration file to the running config of the device.
            NOTE:   Make sure that SCP is allowed and enabled on your devices, e.g.: "ip scp server enable".
            1. Function takes: [[ipaddr, Fullsourcepath, Fulldestinationpath]]
                Windows:    results = await Config.InitiateScpTransfer([["192.168.209.6", "C:\\Python\\Configurator\\192.168.209.6.txt", "flash:192.168.209.6.txt"], [Next...]])
                Linux:      results = await Config.InitiateScpTransfer([["192.168.209.6", "/Python/Configurator/192.168.209.6.txt", "flash:192.168.209.6.txt"], [Next...]])
            print(results)
                Returns:
                    True or False depending on result of transfer.
                        Format is:
                        True: [[True, device ip], [True, next device ip]] etc.
                        False: [[False, device ip, error description], [False, next device ip, error description]] etc.
                        Example:
                            [[False, '192.168.1.1', 'SCP transfer failed. Device: 192.168.1.1 Error: Administratively disabled. Please enable SCP on your device.']]
                    None is returned when connectivity fails for all device(s).
        NOTE:   Both InitiateExecution & InitiateScpTransfer will test connectivity on port 22 before connecting to any device(s).
    asyncio.run(main())
"""
SCRIPT_NAME: str = splitext(basename(executable))[0]+"_Object"
if "python" in SCRIPT_NAME.lower(): SCRIPT_NAME: str = splitext(basename(__file__))[0]
SCRIPT_DIR: str = dirname(realpath(__file__))
CURRENT_DIR: str = getcwd()
if getattr(sys, 'frozen', False):
    CURRENT_DIR: str = dirname(realpath(executable))
if SCRIPT_DIR != CURRENT_DIR:
    chdir(SCRIPT_DIR)
    CURRENT_DIR: str = SCRIPT_DIR

def setup_logger(name: str, log_file: str, log_dir: str, current_dir: str, level=INFO) -> Logger:
    LoggingDir: str = join(current_dir, log_dir)
    if not exists(LoggingDir): mkdir(LoggingDir)
    LoggingFullPath: str = join(current_dir, log_dir, log_file)
    LogFormat: Formatter = Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    LogHandler: handlers.TimedRotatingFileHandler = handlers.TimedRotatingFileHandler(LoggingFullPath, 'midnight', 1, backupCount=90)
    LogHandler.setFormatter(LogFormat)
    logger: getLogger = getLogger(name)
    logger.setLevel(level)
    logger.addHandler(LogHandler)
    return(logger)

PLOG: setup_logger = setup_logger(SCRIPT_NAME, SCRIPT_NAME+".log", SCRIPT_NAME.upper()+"_LOG", CURRENT_DIR)

class Configurator():
    if version_info[0] == 3 and version_info[1] >= 8 and platform.startswith('win'): # Check for operating system
        from asyncio import ProactorEventLoop, WindowsSelectorEventLoopPolicy
        set_event_loop(ProactorEventLoop())
        set_event_loop_policy(WindowsSelectorEventLoopPolicy()) # Bug is not present in Linux
    
    def __init__(self, CLI_USER: str, CLI_PASS: str, CLI_ENABLE: str = "", CONTROLCHAR: list = ["#"], COMMANDTIMEOUT: int = 15, COMMANDSLEEP: float = 0.300, MAX_DEVICE_CONNECTIONS: int = 6, LOGIN_TIMEOUT: int = 30) -> None:
        self.CLI_USER: str = CLI_USER
        self.CLI_PASS: str = CLI_PASS
        self.CLI_ENABLE: str = CLI_ENABLE if CLI_ENABLE else ""
        self.CONTROLCHAR: list = CONTROLCHAR if CONTROLCHAR else ["#"]
        self.COMMANDTIMEOUT: int = COMMANDTIMEOUT if COMMANDTIMEOUT else 15
        self.COMMANDSLEEP: float = COMMANDSLEEP if COMMANDSLEEP else 0.300
        self.MAX_DEVICE_CONNECTIONS: int = MAX_DEVICE_CONNECTIONS if MAX_DEVICE_CONNECTIONS else 6
        self.LOGIN_TIMEOUT: int = LOGIN_TIMEOUT if LOGIN_TIMEOUT else 30
        self.SOCKET_TIMEOUT: int = 1 # Socket timeout
        self.MAX_SOCKET_CONNECTIONS: int = 100 # Number of connections to test at the same time
        self.MAX_BUFFER: int = 65535 # Bytes, do not change, could break the program (65535 is the max possible value)
        self.KEYALGS: list = ["curve25519-sha256","curve25519-sha256@libssh.org","curve448-sha512","ecdh-sha2-nistp521","ecdh-sha2-nistp384","ecdh-sha2-nistp256",
                    "ecdh-sha2-1.3.132.0.10","diffie-hellman-group-exchange-sha256","diffie-hellman-group14-sha256","diffie-hellman-group15-sha512",
                    "diffie-hellman-group16-sha512","diffie-hellman-group17-sha512","diffie-hellman-group18-sha512","diffie-hellman-group14-sha1",
                    "rsa2048-sha256","diffie-hellman-group1-sha1"]
        self.ENCRYPTION: list = ["aes256-ctr", "aes192-ctr", "aes128-ctr", "aes256-cbc", "aes192-cbc", "aes128-cbc"]
    
    CLI_USER: property = property(attrgetter("_CLI_USER"))

    @CLI_USER.setter
    def CLI_USER(self, cliuser: str) -> None:
        if not cliuser: raise Exception("CLI Username cannot be empty.")
        self._CLI_USER: str = cliuser
    
    CLI_PASS: property = property(attrgetter("_CLI_PASS"))

    @CLI_PASS.setter
    def CLI_PASS(self, clipass: str) -> None:
        if not clipass: raise Exception("CLI Password cannot be empty.")
        self._CLI_PASS: str = clipass

    async def TestPortOnNetworkDevice(self, ipaddress: str, commandlist: list, taskQueue: Queue, resultsQueue: Queue) -> None:
        try:
            await sleep(round(uniform(0.01, 0.09), 2))
            ipaddress: str = ipaddress.strip()
            DnsLookup: tuple = gethostbyname_ex(ipaddress)
            if DnsLookup[-1]:
                ipaddress: str = DnsLookup[-1][0]
                loop: AbstractEventLoop = get_event_loop()
                with socket(AF_INET, SOCK_STREAM) as sock: # Create socket stream
                    sock.settimeout(self.SOCKET_TIMEOUT) # Set socket timeout
                    with ThreadPoolExecutor() as executor:
                        for result in as_completed([loop.run_in_executor(executor, sock.connect_ex, (ipaddress,22))]):
                            result: Future
                            results = await result
                            if results == 0: # If SSH connection is successful
                                if commandlist: await resultsQueue.put([ipaddress, 22, commandlist])
                                else: await resultsQueue.put([ipaddress, 22])
                            else: # If connection attempts failed
                                await resultsQueue.put([ipaddress, "Not Available", ["Error: Could not connect to: "+ipaddress]])
                                PLOG.info("[ TestPortOnNetworkDevice ]: Could not connect to: "+ipaddress)
            else: PLOG.info("[ TestPortOnNetworkDevice ]: Unable to resolve: "+ipaddress)
            taskQueue.task_done()
            taskQueue.get_nowait()
        except Exception as e:
            e: str = str(e)
            PLOG.info("[ TestPortOnNetworkDevice ] [ "+ipaddress+" ] Exception occurred ("+e+"), traceback:", exc_info=True)
            exit()

    async def CheckDeviceConnectivity(self, deviceList: list) -> list:
        try:
            CheckConnectivity: list = []
            AppendResults = CheckConnectivity.append
            taskQueue: Queue = Queue(maxsize=self.MAX_SOCKET_CONNECTIONS)
            resultsQueue: Queue = Queue()
            for device in deviceList:
                device: list
                if len(device) > 1:
                    await taskQueue.put(create_task(self.TestPortOnNetworkDevice(device[0], device[1], taskQueue, resultsQueue)))
                else:
                    await taskQueue.put(create_task(self.TestPortOnNetworkDevice(device[0], [], taskQueue, resultsQueue)))
            await taskQueue.join()
            while not resultsQueue.empty():
                AppendResults(await resultsQueue.get())
                resultsQueue.task_done()
            await resultsQueue.join()
            PLOG.info("[ CheckDeviceConnectivity ]: Checking device connectivity... [ COMPLETED ]")
            return(CheckConnectivity)
        except Exception as e:
            e: str = str(e)
            PLOG.info("[ CheckDeviceConnectivity ] Exception occurred ("+e+"), traceback:", exc_info=True)
            exit()

    async def ClearBuffer(self, _stdin, _stdout, controlchar: list) -> str:
        try:
            timer: float = 0.0
            error: int = 0
            retry: int = 0
            buffer: str = ""
            await sleep(self.COMMANDSLEEP)
            while not any(buffer.endswith(i) for i in controlchar):
                if retry > 2 or error == 1:
                    if error == 0:
                        error: int = 1
                        if "% Access denied" in buffer:
                            errorDescription: str = " Unable to enter enable mode on device (access denied), buffer from switch:\n"+buffer.strip()
                        else:
                            errorDescription: str = " Reached timeout when trying to clear buffer:\n"+buffer.strip()
                    break
                output: str = _stdout.read(self.MAX_BUFFER)
                try:
                    buffer += await wait_for(output, 10)
                except TimeoutError:
                    if buffer.endswith(">") and self.CLI_ENABLE:
                        _stdin.write("enable\n")
                        await sleep(self.COMMANDSLEEP)
                        _stdin.write(self.CLI_ENABLE+"\n")
                        await sleep(self.COMMANDSLEEP)
                        while buffer.endswith(">"):
                            output: str = _stdout.read(self.MAX_BUFFER)
                            try:
                                buffer += await wait_for(output, 2.5)
                            except TimeoutError:
                                errorDescription: str = " Unable to enter enable mode on device (access denied), buffer from switch:\n"+buffer.strip()
                                error: int = 1
                                break
                            if any(buffer.endswith(i) for i in controlchar):
                                break
                            if timer > 2.5:
                                errorDescription: str = " Unable to enter enable mode on device (access denied), buffer from switch:\n"+buffer.strip()
                                error: int = 1
                                break
                            timer += self.COMMANDSLEEP
                            await sleep(self.COMMANDSLEEP)
                        retry += 1
                        continue
                    elif buffer.endswith(">"):
                        _stdin.write("enable\n")
                        await sleep(self.COMMANDSLEEP)
                        _stdin.write(self.CLI_PASS+"\n")
                        await sleep(self.COMMANDSLEEP)
                        retry += 1
                        continue
                    retry += 1
                    continue
                if retry < 3:
                    _stdin.write("\n")
                    await sleep(self.COMMANDSLEEP)
                    _stdin.write("\n")
                    await sleep(self.COMMANDSLEEP)
                retry += 1
            return(buffer.strip()) if error != 1 else errorDescription
        except BrokenPipeError as e:
            e: str = str(e)
            if "authorization failed" in buffer.lower():
                errorDescription: str = " Reached timeout, Username: "+self.CLI_USER+" does not have the necessary rights to fully access this device:\n"+buffer.strip()
            else: errorDescription: str = " Reached timeout, terminal was disconnected while active ("+e+"):\n"+buffer.strip()
            return(errorDescription)
        except Exception as e:
            e: str = str(e)
            PLOG.info("[ ClearBuffer ] Exception occurred ("+e+"), traceback:", exc_info=True)
            exit()

    async def ExecuteSingleCommand(self, command: str, _stdin, _stdout, controlchar: list, commandtimeout: int) -> str:
        try:
            error: int = 0
            buffer: str = ""
            _stdin.write(command+"\n")
            await sleep(self.COMMANDSLEEP)
            while not any(buffer.endswith(i) for i in controlchar):
                if error > 0:
                    break
                output: str = _stdout.read(self.MAX_BUFFER)
                try:
                    buffer += await wait_for(output, commandtimeout)
                except TimeoutError:
                    if "continue?" in buffer:
                        _stdin.write("y\n")
                        await sleep(self.COMMANDSLEEP)
                        continue
                    elif "really sure" in buffer:
                        _stdin.write("y\n")
                        await sleep(self.COMMANDSLEEP)
                        continue
                    elif "confirm" in buffer:
                        _stdin.write("\n\n")
                        await sleep(self.COMMANDSLEEP)
                        continue
                    elif "SHUTDOWN" in buffer:
                        _stdin.write("\n\n")
                        await sleep(self.COMMANDSLEEP)
                        continue
                    elif buffer.endswith("]? "):
                        _stdin.write("\n\n")
                        await sleep(self.COMMANDSLEEP)
                        continue
                    else:
                        errorDescription: str = " Reached timeout when executing command: [ "+command+" ] - buffer from switch:\n"+buffer.strip()
                        error: int = 1
                        break
                if "Invalid input detected" in buffer:
                    bufferdesc: list = [x.strip() for x in buffer.strip().replace("\r", "").splitlines() if x]
                    error: int = 1
                    errorDescription: str = " Invalid input detected: "+" - ".join(bufferdesc)
                    continue
                if "Unknown command or computer name" in buffer:
                    bufferdesc: list = [x.strip() for x in buffer.strip().replace("\r", "").splitlines() if x]
                    error: int = 1
                    errorDescription: str = " Unknown command or computer name: "+" - ".join(bufferdesc)
                    continue
            return(buffer.strip().replace('\x08','').replace('\x07','')) if error != 1 else errorDescription
        except Exception as e:
            e: str = str(e)
            PLOG.info("[ ExecuteSingleCommand ] Exception occurred ("+e+"), traceback:", exc_info=True)
            exit()

    async def ExecuteCommands(self, device_ip: str, port: int, commandlist: list, taskQueue: Queue, resultsQueue: Queue, controlchar: list, commandtimeout: int, retry: bool = False) -> None:
        try:
            async with await wait_for(connect(device_ip, port, username=self.CLI_USER, password=self.CLI_PASS, known_hosts=None, options=SSHClientConnectionOptions(encryption_algs=self.ENCRYPTION, kex_algs=self.KEYALGS)), timeout=self.LOGIN_TIMEOUT) as connection:
                _stdin, _stdout, _ = await connection.open_session(term_type="Dumb", term_size=(300, 24))
                clear_shell: str = await self.ClearBuffer(_stdin, _stdout, controlchar)
                total_commands: int = len(commandlist)
                command_counter: int = 1
                if "Reached timeout" not in clear_shell and "Unable to enter enable mode" not in clear_shell:
                    hostname: str = clear_shell.splitlines()[-1]
                    temp: list = []
                    AppendTemp = temp.append
                    for command in commandlist:
                        command: str
                        if not command.startswith("!"):
                            result: str = await self.ExecuteSingleCommand(command, _stdin, _stdout, controlchar, commandtimeout)
                            if "Reached timeout" not in result:
                                if "Invalid input detected" in result:
                                    AppendTemp("Device: "+device_ip+" Error:"+result.rstrip(" - "+hostname)+" [ SKIPPED ]")
                                    PLOG.info("[ ExecuteCommands ]: Device: "+device_ip+result.rstrip(" - "+hostname))
                                elif "Unknown command or computer name" in result:
                                    AppendTemp("Device: "+device_ip+" Error:"+result.rstrip(" - "+hostname)+" [ SKIPPED ]")
                                    PLOG.info("[ ExecuteCommands ]: Device: "+device_ip+result.rstrip(" - "+hostname))
                                else:
                                    tmpResult: str = result.replace('\r', '').replace(hostname, '').replace(command, '').strip()
                                    if tmpResult:
                                        AppendTemp(result.replace('\r', '').rstrip(hostname))
                                    else: PLOG.info("[ ExecuteCommands ]: Device: "+device_ip+" command: [ "+command.rstrip()+" ] [ OK ]")
                            else:
                                if "--more--" in result.lower(): AppendTemp("Device: "+device_ip+" Error: Reached timeout: Looks like paging is enabled [ SKIPPED ]")
                                else: AppendTemp("Device: "+device_ip+" Error: Reached timeout after entering command [ "+command.rstrip()+" ] [ SKIPPED ]")
                                PLOG.info("[ ExecuteCommands ]: Device: "+device_ip+result.replace('\r', ''))
                            if command_counter == total_commands:
                                PLOG.info("[ ExecuteCommands ]: Device: "+device_ip+" Command: "+str(command_counter)+" out of "+str(total_commands)+" [ COMPLETED ]")
                            command_counter += 1
                    await resultsQueue.put([device_ip, hostname, temp])
                else:
                    if "Unable to enter enable mode" in clear_shell or clear_shell.strip().endswith(">"):
                        await resultsQueue.put([device_ip, "Not Available", ["Device: "+device_ip+" Error: Reached timeout: Unable to enter enable mode on device (access denied) [ SKIPPED ]"]])
                    elif "terminal was disconnected" in clear_shell:
                        await resultsQueue.put([device_ip, "Not Available", ["Device: "+device_ip+" Error: Reached timeout: Terminal was disconnected while active (Channel not open for sending) [ SKIPPED ]"]])
                    elif "Reached timeout, Username:" in clear_shell:
                        await resultsQueue.put([device_ip, "Not Available", ["Device: "+device_ip+" Error: Reached timeout: Username: "+self.CLI_USER+" does not have the necessary rights to fully access this device (% Authorization Failed) [ SKIPPED ]"]])
                    else: await resultsQueue.put([device_ip, "Not Available", ["Device: "+device_ip+" Error: Reached timeout while trying to clear buffer [ SKIPPED ]"]])
                    PLOG.info("[ ExecuteCommands ]: Device: "+device_ip+clear_shell)
                taskQueue.task_done()
                taskQueue.get_nowait()
        except ConnectionResetError as e:
            if not retry: await self.ExecuteCommands(device_ip, port, commandlist, taskQueue, resultsQueue, controlchar, commandtimeout, True)
            else:
                e: str = str(e)
                PLOG.info("[ ExecuteCommands ] Unable to connect to Device: "+device_ip+", "+e+" (Connection reset by peer).")
                await resultsQueue.put([device_ip, "Not Available", ["Device: "+device_ip+" Error: Unable to connect. "+e+" (Connection reset by peer) [ SKIPPED ]"]])
                taskQueue.task_done()
                taskQueue.get_nowait()
        except PermissionDenied:
            PLOG.info("[ ExecuteCommands ] Unable to connect to Device: "+device_ip+", Unauthorized for Username: "+self.CLI_USER+" (Permission Denied).")
            await resultsQueue.put([device_ip, "Not Available", ["Device: "+device_ip+" Error: Unable to connect. Unauthorized for Username: "+self.CLI_USER+" (Permission Denied) [ SKIPPED ]"]])
            taskQueue.task_done()
            taskQueue.get_nowait()
        except TimeoutError as e:
            if not retry: await self.ExecuteCommands(device_ip, port, commandlist, taskQueue, resultsQueue, controlchar, commandtimeout, True)
            else:
                e: str = str(e)
                PLOG.info("[ ExecuteCommands ] Connection timed out for device: "+device_ip+", "+e+" (Connect call failed).")
                await resultsQueue.put([device_ip, "Not Available", ["Device: "+device_ip+" Error: Connection timed out. "+e+" (Connect call failed) [ SKIPPED ]"]])
                taskQueue.task_done()
                taskQueue.get_nowait()
        except Exception as e:
            e: str = str(e)
            PLOG.info("[ ExecuteCommands ] Exception occurred ("+e+"), traceback:", exc_info=True)
            await resultsQueue.put([device_ip, "Not Available", ["Device: "+device_ip+" Error: Exception occurred: [ "+e+" ] - Commands: "+str(commandlist)+" [ SKIPPED ]"]])
            taskQueue.task_done()
            taskQueue.get_nowait()

    async def InitiateExecution(self, DEVICELIST: list, COMMANDLIST: list = []) -> list:
        PLOG.info("\n\n------------------------------------\n-------STARTING: CLI EXECUTION------\n------------------------------------\n")
        returnResults: list = []
        AppendResults = returnResults.append
        try:
            if DEVICELIST:
                DEVICELIST: list = await self.CheckDeviceConnectivity(DEVICELIST)
                if DEVICELIST:
                    taskQueue: Queue = Queue(maxsize=self.MAX_DEVICE_CONNECTIONS)
                    resultsQueue: Queue = Queue()
                    for device in DEVICELIST:
                        device: list
                        if len(device) > 2 and "Error" in device[2][0]:
                            await resultsQueue.put(device)
                            continue
                        if COMMANDLIST:
                            await taskQueue.put(create_task(self.ExecuteCommands(device[0], device[1], COMMANDLIST, taskQueue, resultsQueue, self.CONTROLCHAR, self.COMMANDTIMEOUT)))
                        else:
                            if isinstance(device[2], list) and device[2]:
                                await taskQueue.put(create_task(self.ExecuteCommands(device[0], device[1], device[2], taskQueue, resultsQueue, self.CONTROLCHAR, self.COMMANDTIMEOUT)))
                        await sleep(round(uniform(0.25, 0.30), 2))
                    await taskQueue.join()
                    while not resultsQueue.empty():
                        result: list = await resultsQueue.get()
                        AppendResults(result)
                        resultsQueue.task_done()
                    await resultsQueue.join()
            else:
                PLOG.info("[ InitiateExecution ] No device list received.")
            return(returnResults)
        except Exception as e:
            e: str = str(e)
            PLOG.info("[ InitiateExecution ] Exception occurred ("+e+"), traceback:", exc_info=True)
            exit()

    async def TransferFile(self, deviceip: str, port: int, source: str, dest: str, transferQueue: Queue, transferQueueResults: Queue) -> None:
        try:
            async with await wait_for(connect(deviceip, port, username=self.CLI_USER, password=self.CLI_PASS, known_hosts=None, options=SSHClientConnectionOptions(encryption_algs=self.ENCRYPTION, kex_algs=self.KEYALGS)), timeout=self.LOGIN_TIMEOUT) as connection:
                await scp(source, (connection, dest))
            PLOG.info("[ TransferFile ]: Upload to device: "+deviceip+" ("+dest+") [ COMPLETED ]")
            await transferQueueResults.put([deviceip, True, dest])
            transferQueue.task_done()
            transferQueue.get_nowait()
        except Exception as e:
            e: str = str(e)
            if "Administratively disabled" in e:
                error: str = "SCP transfer failed. Device: "+deviceip+" Error: "+e+" Please enable SCP on your device."
                PLOG.info("[ TransferFile ]: SCP failed. Device: "+deviceip+" Error: "+e+" Please enable SCP on your device.")
            else:
                error: str = "SCP transfer failed. Device: "+deviceip+" Error: "+e
                PLOG.info("[ TransferFile ]: SCP failed. Device: "+deviceip+" Error: "+e)
            await transferQueueResults.put([deviceip, False, error])
            transferQueue.task_done()
            transferQueue.get_nowait()

    async def InitiateScpTransfer(self, ListOfDevicesAndFilenames: list) -> list:
        PLOG.info("\n\n------------------------------------\n-------STARTING: SCP TRANSFER-------\n------------------------------------\n")
        returnResults: list = []
        AppendResults = returnResults.append
        try:
            DeviceConnectivity: list = [[x[0]] for x in ListOfDevicesAndFilenames]
            ConnectedDevices: list = await self.CheckDeviceConnectivity(DeviceConnectivity)
            if ConnectedDevices:
                ListOfDevices: list = [[x[0], x[1], d[1], d[2]] for x in ConnectedDevices for d in ListOfDevicesAndFilenames if x[0] == d[0]]
                transferQueue: Queue = Queue(maxsize=self.MAX_DEVICE_CONNECTIONS)
                transferQueueResults: Queue = Queue()
                for device in ListOfDevices:
                    device: list
                    await transferQueue.put(create_task(self.TransferFile(device[0], device[1], device[2], device[3], transferQueue, transferQueueResults)))
                    await sleep(round(uniform(0.25, 0.30), 2))
                await transferQueue.join()
                while not transferQueueResults.empty():
                    result: list = await transferQueueResults.get()
                    AppendResults(result)
                    transferQueueResults.task_done()
                await transferQueueResults.join()
            return(returnResults)
        except Exception as e:
            e: str = str(e)
            PLOG.info("[ InitiateScpTransfer ] Exception occurred ("+e+"), traceback:", exc_info=True)
            exit()