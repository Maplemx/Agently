import os
import json
import sqlite3
from .utils import StorageABC

class SQLite(StorageABC):
    def __init__(self, db_name: str="default", settings: object={}):
        self.settings = settings
        self.path = self.settings.get("storage.SQLite.path") or None
        self.file_name = self.settings.get("storage.SQLite.file_name") or ".Agently.db"
        if self.path and not self.path.endswith("/"):
            self.path = self.path + "/"
        if not self.file_name.endswith(".db"):
            self.file_name = self.file_name + ".db"
        self.db = f"{ self.path }{ self.file_name }" if self.path else self.file_name
        self.space_name = db_name
        self.conn = None
        self.cursor = None

    def __connect(self):
        self.conn = sqlite3.connect(self.db)
        self.cursor = self.conn.cursor()

    def __connect_if_exists(self):
        if os.path.exists(self.db):
            self.conn = sqlite3.connect(self.db)
            self.cursor = self.conn.cursor()
            return True
        else:
            return False
    
    def __close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __commit_and_close(self):
        if self.conn:
            self.conn.commit()
            self.cursor.close()
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __create_table_if_not_exists(self, table_name: str):
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS `{ self.space_name }_{ table_name }` (key TEXT PRIMARY KEY, value TEXT)")
    
    def __drop_table_if_exists(self, table_name: str):
        self.cursor.execute(f"DROP TABLE IF EXISTS `{ self.space_name }_{ table_name }`")
    
    def set(self, table_name: str, key: str, value: any):
        self.__connect()
        self.__create_table_if_not_exists(table_name)
        self.cursor.execute(
f"""INSERT INTO `{ self.space_name }_{ table_name }` (`key`, `value`)
    VALUES (?, ?)
    ON CONFLICT(`key`)
    DO UPDATE SET `key`=excluded.key, `value`=excluded.value
""",
            (key, json.dumps(value))
        )
        self.__commit_and_close()
        return self

    def set_all(self, table_name:str, full_data: dict):
        self.__connect()
        self.__drop_table_if_exists(table_name)
        self.__create_table_if_not_exists(table_name)
        for key, value in full_data.items():
            self.set(table_name, key, value)
        self.__commit_and_close()
        return self

    def remove(self, table_name: str, key: str):
        self.__connect()
        self.__create_table_if_not_exists(table_name)
        self.cursor.execute(f"DELETE FROM `{ self.space_name }_{ table_name }` WHERE `key` = ?", (key,))
        self.__commit_and_close()
        return self

    def update(self, table_name:str, update_data: dict):
        self.__connect()
        self.__create_table_if_not_exists(table_name)
        for key, value in update_data.items():
            self.set(table_name, key, value)
        self.__commit_and_close()
        return self

    def get(self, table_name: str, key: str):
        if self.__connect_if_exists():
            try:
                self.cursor.execute(f"SELECT `value` FROM `{ self.space_name }_{ table_name }` WHERE `key` = ?", (key,))
                result = self.cursor.fetchone()
            except sqlite3.OperationalError as e:
                result = None
            self.__close()
            if result:
                return json.loads(result[0])
            else:
                return None
        else:
            return None

    def get_all(self, table_name: str, keys: (list, None)=None):
        if self.__connect_if_exists():
            if keys:            
                result = {}
                for key in keys:
                    value = self.get(table_name, key)
                    if value:
                        result.update({ key: value })
                    else:
                        result.update({ key: None })
                self.__close()
                return result
            else:
                table_data = {}
                try:
                    self.cursor.execute(f"SELECT `key`, `value` FROM `{ self.space_name }_{ table_name }`")
                    results = self.cursor.fetchall()
                except sqlite3.OperationalError as e:
                    results = []
                for row in results:
                    key, value = row[0], json.loads(row[1])
                    table_data.update({ key: value })
                self.__close()
                return table_data
        else:
            return {}

def export():
    return ("SQLite", SQLite)