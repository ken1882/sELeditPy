import os
import shutil
import struct
from typing import List, Any
import codecs

class eList:
    def __init__(self):
        self.list_name = ""
        self.list_offset = bytearray()  # -> length from config file, values from elements.data
        self.list_type = 0
        self.element_size = 0
        self.element_fields = []  # -> length & values from config file
        self.element_types = []  # -> length & values from config file
        self.element_values = []  # list.length from elements.data, elements.length from config file

    def get_value(self, element_index: int, field_index: int) -> str:
        if field_index > -1:
            value = self.element_values[element_index][field_index]
            value_type = self.element_types[field_index]

            if value_type == "int16":
                return str(int.from_bytes(value, byteorder='little', signed=True))
            elif value_type == "int32":
                return str(int.from_bytes(value, byteorder='little', signed=True))
            elif value_type == "int64":
                return str(int.from_bytes(value, byteorder='little', signed=True))
            elif value_type == "float":
                return "{:.6f}".format(struct.unpack('<f', value)[0])
            elif value_type == "double":
                return "{:.6f}".format(struct.unpack('<d', value)[0])
            elif "byte:" in value_type:
                return value.hex().upper()
            elif "wstring:" in value_type:
                return value.decode("utf-16").split('\0')[0]
            elif "string:" in value_type:
                return value.decode("GBK").split('\0')[0]
        return ""

    def set_value(self, element_index: int, field_index: int, value: str):
        value_type = self.element_types[field_index]

        if value_type == "int16":
            self.element_values[element_index][field_index] = int(value).to_bytes(2, byteorder='little', signed=True)
        elif value_type == "int32":
            self.element_values[element_index][field_index] = int(value).to_bytes(4, byteorder='little', signed=True)
        elif value_type == "int64":
            self.element_values[element_index][field_index] = int(value).to_bytes(8, byteorder='little', signed=True)
        elif value_type == "float":
            self.element_values[element_index][field_index] = struct.pack('<f', float(value))
        elif value_type == "double":
            self.element_values[element_index][field_index] = struct.pack('<d', float(value))
        elif "byte:" in value_type:
            self.element_values[element_index][field_index] = bytes.fromhex(value.replace('-', ''))
        elif "wstring:" in value_type:
            encoded = value.encode("utf-16")[2:]  # Remove BOM
            self.element_values[element_index][field_index] = encoded[:int(value_type.split(':')[1])]
        elif "string:" in value_type:
            encoded = value.encode("GBK")
            self.element_values[element_index][field_index] = encoded[:int(value_type.split(':')[1])]

    def remove_item(self, item_index: int):
        del self.element_values[item_index]

    def add_item(self, item_values: List[Any]):
        self.element_values.append(item_values)

    def export_item(self, file: str, index: int):
        with codecs.open(file, "w", encoding="utf-16") as f:
            for i, field in enumerate(self.element_fields):
                f.write(f'{field}({self.element_types[i]})="{self.get_value(index, i)}"\n')

    def import_item(self, file: str, index: int):
        with codecs.open(file, "r", encoding="utf-16") as f:
            for i, _ in enumerate(self.element_types):
                field = f.readline().strip()
                if not field.startswith("#") and not field.startswith("//") and field:
                    value = field.split("=")[1].strip('"')
                    self.set_value(index, i, value)

    def join_elements(self, new_list: 'eList', list_id: int, add_new: bool, backup_new: bool, replace_changed: bool,
                        backup_changed: bool, remove_missing: bool, backup_missing: bool, dir_backup_new: str,
                        dir_backup_changed: str, dir_backup_missing: str):
        report = []
        new_element_values = new_list.element_values

        # Check for missing items
        for n, element in enumerate(self.element_values):
            exists = any(self.get_value(n, 0) == new_list.get_value(e, 0) for e in range(len(new_element_values)))
            if not exists:
                if dir_backup_missing and os.path.exists(dir_backup_missing):
                    self.export_item(os.path.join(dir_backup_missing, f"List_{list_id}_Item_{self.get_value(n, 0)}.txt"), n)
                if remove_missing:
                    report.append(f"- MISSING ITEM (*removed): {self.get_value(n, 0)}")
                    self.remove_item(n)
                else:
                    report.append(f"- MISSING ITEM (*not removed): {self.get_value(n, 0)}")

        # Check for new or changed items
        for e, new_element in enumerate(new_element_values):
            exists = False
            for n, element in enumerate(self.element_values):
                if self.get_value(n, 0) == new_list.get_value(e, 0):
                    exists = True
                    if len(self.element_values[n]) != len(new_list.element_values[e]):
                        report.append(f"<> DIFFERENT ITEM (*not replaced, invalid amount of values): {self.get_value(n, 0)}")
                    else:
                        for i in range(len(self.element_values[n])):
                            if self.get_value(n, i) != new_list.get_value(e, i):
                                if backup_changed and os.path.exists(dir_backup_changed):
                                    self.export_item(os.path.join(dir_backup_changed, f"List_{list_id}_Item_{self.get_value(n, 0)}.txt"), n)
                                if replace_changed:
                                    self.element_values[n] = new_list.element_values[e]
                                    report.append(f"<> DIFFERENT ITEM (*replaced): {self.get_value(n, 0)}")
                                else:
                                    report.append(f"<> DIFFERENT ITEM (*not replaced): {self.get_value(n, 0)}")
                                break
                    break

            if not exists:
                if backup_new and os.path.exists(dir_backup_new):
                    new_list.export_item(os.path.join(dir_backup_new, f"List_{list_id}_Item_{new_list.get_value(e, 0)}.txt"), e)
                if add_new:
                    self.add_item(new_element)
                    report.append(f"+ NEW ITEM (*added): {self.get_value(-1, 0)}")
                else:
                    report.append(f"+ NEW ITEM (*not added): {self.get_value(-1, 0)}")

        return report
