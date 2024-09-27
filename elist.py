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

    def to_dict(self):
        ret = {
            'list_name': self.list_name,
            'list_type': self.list_type,
            'list_size': self.element_size,
            'element_types': self.element_types,
            'element_fields': self.element_fields,
            'element_values': [],
        }
        ENCODINGS = ['utf16', 'GBK', 'utf8','GB2312']
        for dat in self.element_values:
            obj = {}
            for i,f in enumerate(dat):
                if 'string' in self.element_types[i]:
                    for enc in ENCODINGS:
                        ss = f
                        try:
                            ss = f.decode(enc).rstrip('\x00')
                            break
                        except Exception:
                            pass
                    obj[self.element_fields[i]] = ss
                else:
                    obj[self.element_fields[i]] = f
            ret['element_values'].append(obj)
        return ret
