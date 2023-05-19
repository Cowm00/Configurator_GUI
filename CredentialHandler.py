# -*- coding: utf-8 -*-
# Written by Rune Johannesen, (c)2021-2023
from subprocess import run
from sys import platform
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from base64 import urlsafe_b64encode
from os.path import expanduser, splitext, basename, exists
from sqlite3 import connect, Cursor
from traceback import format_exc

class CredentialHandler():
    def __init__(self, db: str) -> None:
        """db: string <> Directory path and name of database to save data to. db must contain the full directory path.
        Example: c:\\user\\test\\database.db"""
        self.KDF: str = PBKDF2HMAC(algorithm=hashes.SHA512(),length=32,salt=self.CreateMachineUUID(),iterations=400000,backend=default_backend())
        self.FERNET_KEY: bytes = urlsafe_b64encode(self.KDF.derive(expanduser("~").encode()))
        self.db: str = db
        if not self.db.endswith(".db"): self.db = f"{self.db}.db"
        self.script_name: str = splitext(basename(__file__))[0]

    def save_creds(self, device_file: str, username: str, password: str) -> None:
        verify: int = self.sql_execute([f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{self.script_name}'"])[0][0]
        if not verify:
            self.sql_execute([f"CREATE TABLE {self.script_name}(id INTEGER PRIMARY KEY, device_file TEXT, username TEXT, password TEXT)"])
        self.sql_execute([f"INSERT OR REPLACE INTO {self.script_name} VALUES(0,'{self.encryptString(device_file)}','{self.encryptString(username)}','{self.encryptString(password)}')"])

    def load_creds(self) -> tuple:
        verify: int = self.sql_execute([f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{self.script_name}'"])[0][0]
        if not verify:
            return(None,None,None)
        else:
            try:
                data: tuple = self.sql_execute([f"SELECT * FROM {self.script_name}"])[0]
                return(self.decryptString(data[1]), self.decryptString(data[2]), self.decryptString(data[3]))
            except: return(None,None,None)

    def encryptString(self, string: str) -> str:
        cipher: Fernet = Fernet(self.FERNET_KEY)
        return(cipher.encrypt(string.encode()).decode())

    def decryptString(self, string: str) -> str:
        cipher: Fernet = Fernet(self.FERNET_KEY)
        return(cipher.decrypt(string.encode()).decode())

    def sql_execute(self, sqlcmdlist: list) -> list:
        """sqlcmdlist: list (Required) List of sql commands to execute on the database"""
        returnResults: list = []
        init: bool = False
        if not exists(self.db):
            init: bool = True
        try:
            with connect(self.db) as connection:
                cursor: Cursor = connection.cursor()
                if init:
                    cursor.execute(f"CREATE TABLE {self.script_name}(id INTEGER PRIMARY KEY, device_file TEXT, username TEXT, password TEXT)")
                    connection.commit()
                for cmd in sqlcmdlist:
                    if isinstance(cmd, str):
                        if "select" in cmd.lower():
                            for entry in cursor.execute(cmd).fetchall():
                                returnResults.append(entry)
                        if "update" in cmd.lower() or "create" in cmd.lower() or "drop" in cmd.lower() or "replace" in cmd.lower() or "insert" in cmd.lower():
                            cursor.execute(cmd)
                            connection.commit()
        except:
            raise Exception(f"{self.script_name} <> sql_execute: Failed to execute, full traceback\n:{format_exc()}")
        return(returnResults)

    def CreateMachineUUID(self) -> bytes:
        def _run(cmd: str) -> bytes:
            try: return(run(cmd, shell=True, capture_output=True, check=True, encoding="utf-8").stdout.strip().encode())
            except: return(b"")
        os_type: str = platform.lower()
        if "win" in os_type:
            commands: list = ["wmic bios get Manufacturer", "wmic bios get SerialNumber"]
            return(b"".join([_run(x).replace(b"\r",b"").replace(b"\n",b"").replace(b" ",b"") for x in commands]))
        if "darwin" in os_type:
            commands: list = ["ioreg -c IOPlatformExpertDevice -d 2 | awk -F\" '/IOPlatformSerialNumber/{print $(NF-1)}'", "ioreg -c IOPlatformExpertDevice -d 2 | awk -F\" '/manufacturer/{print $(NF-1)}'"]
            return(b"".join([_run(x).replace(b"\r",b"").replace(b"\n",b"").replace(b" ",b"") for x in commands]))
        if os_type.startswith("linux"):
            return(_run('cat /etc/machine-id')) if _run('cat /etc/machine-id') else _run('cat /var/lib/dbus/machine-id')