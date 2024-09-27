import os
import struct
import pprint as pp
from glob import glob
from elist import eList
import json

Version = 0
Signature = None
ConversationListIndex = 0
Listcnts = None
ListOsets = None
Listver = -1
SStat = [0, 0, 0, 0, 0]

def load_configuration(file):
    global ConversationListIndex
    with open(file, 'r') as sr:
        Li = [eList() for _ in range(int(sr.readline().strip()))]
        try:
            ConversationListIndex = int(sr.readline().strip())
        except:
            ConversationListIndex = 58
        for i in range(len(Li)):
            line = sr.readline().strip()
            while line == "":
                line = sr.readline().strip()
            Li[i].list_name = line
            Li[i].list_offset = None
            offset = sr.readline().strip()
            if offset != "AUTO":
                Li[i].listOffset = [None] * int(offset)
            Li[i].element_fields = sr.readline().strip().split(';')
            Li[i].element_types = sr.readline().strip().split(';')
    return Li


def read_value(br, value_type: str):
    try:
        if value_type == "int16":
            return struct.unpack('<h', br.read(2))[0]  # '<h' is little-endian int16
        if value_type == "int32":
            return struct.unpack('<i', br.read(4))[0]  # '<i' is little-endian int32
        if value_type == "int64":
            return struct.unpack('<q', br.read(8))[0]  # '<q' is little-endian int64
        if value_type == "float":
            return struct.unpack('<f', br.read(4))[0]  # '<f' is little-endian float
        if value_type == "double":
            return struct.unpack('<d', br.read(8))[0]  # '<d' is little-endian double
        if "byte:" in value_type:
            size = int(value_type.split(":")[1])
            return br.read(size)
        if "wstring:" in value_type:
            size = int(value_type.split(":")[1])
            return br.read(size)
        if "string:" in value_type:
            size = int(value_type.split(":")[1])
            return br.read(size)
    except Exception as err:
        print("Error: ", err)
    return None

def write_value(bw, value, value_type: str):
    if value_type == "int16":
        bw.write(struct.pack('<h', value))  # Write int16
        return
    if value_type == "int32":
        bw.write(struct.pack('<i', value))  # Write int32
        return
    if value_type == "int64":
        bw.write(struct.pack('<q', value))  # Write int64
        return
    if value_type == "float":
        bw.write(struct.pack('<f', value))  # Write float
        return
    if value_type == "double":
        bw.write(struct.pack('<d', value))  # Write double
        return
    if "byte:" in value_type:
        bw.write(value)  # Write byte array
        return
    if "wstring:" in value_type:
        bw.write(value)  # Write wide string byte array
        return
    if "string:" in value_type:
        bw.write(value)  # Write string byte array
        return

def Load(el_file):
    global Listcnts, ListOsets, Listver, SStat, Version, Signature
    Li = []
    addonIndex = {}
    Listcnts = None
    ListOsets = None
    Listver = -1
    SStat = [0, 0, 0, 0, 0]
    fileStream = os.path.join(os.path.dirname(el_file), "elements.list.count")
    if os.path.exists(fileStream):
        Listcnts = {}
        ListOsets = {}
        with open(fileStream, 'r') as reader:
            for line in reader:
                val = line.strip().split('=')
                if val[0] == "ver":
                    Listver = int(val[1])
                elif val[0] == "offset":
                    ListOsets[val[1]] = val[2]
                else:
                    Listcnts[val[0]] = val[1]
    # Open the element file
    with open(el_file, 'rb') as fs:
        br = fs
        Version = struct.unpack('h', br.read(2))[0]
        if Listver > -1:
            Version = Listver
        Signature = struct.unpack('h', br.read(2))[0]
        # Check if a corresponding configuration file exists
        configFiles = glob(f"configs/PW_*_v{Version}.cfg")
        if configFiles:
            ConfigFile = configFiles[0]
            Li = load_configuration(ConfigFile)
            print('CL index:', ConversationListIndex)
            len_st = len(Li)
            # Read the element file
            for l in range(len_st):
                print(f"Process {l} of {len_st}")
                SStat[0] = l
                # Read offset
                if Li[l].list_offset is not None:
                    if len(Li[l].list_offset) > 0:
                        Li[l].list_offset = br.read(len(Li[l].list_offset))
                else:
                    # Auto-detect offset (for list 20 & 100)
                    if l == 0:
                        t = br.read(4)
                        length = struct.unpack('i', br.read(4))[0]
                        buffer = br.read(length)
                        Li[l].list_offset = t + length.to_bytes(4, byteorder='little') + buffer
                    elif l == 20:
                        tag = br.read(4)
                        length = struct.unpack('i', br.read(4))[0]
                        buffer = br.read(length)
                        t = br.read(4)
                        Li[l].listOffset = tag + length.to_bytes(4, byteorder='little') + buffer + t
                    NPC_WAR_TOWERBUILD_SERVICE_index = 100 if Version < 191 else 99
                    if l == NPC_WAR_TOWERBUILD_SERVICE_index:
                        tag = br.read(4)
                        length = struct.unpack('i', br.read(4))[0]
                        buffer = br.read(length)
                        Li[l].listOffset = tag + length.to_bytes(4, byteorder='little') + buffer
                # Read conversation list
                if l == ConversationListIndex:
                    if Version >= 191:
                        sourcePosition = fs.tell()
                        endPosition = fs.seek(0, 2)
                        listLength = endPosition - sourcePosition
                        fs.seek(sourcePosition)
                        Li[l].element_types[0] = f"byte:{listLength}"
                        print("CL length:", listLength)
                    else:
                        # Auto detect only works for specific files
                        if "AUTO" in Li[l].element_types[0]:
                            pattern = "facedata\\".encode("GBK")
                            sourcePosition = fs.tell()
                            listLength = -72 - len(pattern)
                            run = True
                            while run:
                                run = False
                                for i in range(len(pattern)):
                                    listLength += 1
                                    if br.read(1) != pattern[i:i+1]:
                                        run = True
                                        break
                            fs.seek(sourcePosition)
                            Li[l].element_types[0] = f"byte:{listLength}"
                    Li[l].element_values = [[None] * len(Li[l].element_types)]
                    Li[l].element_values[0][0] = read_value(br, Li[l].element_types[0])
                else:
                    if Version >= 191:
                        Li[l].list_type = struct.unpack('i', br.read(4))[0]
                    if Listver > -1 and str(l) in Listcnts:
                        num = int(Listcnts[str(l)])
                        Li[l].element_values = [[None] * len(Li[l].element_types)] * num
                        br.read(4)
                    else:
                        num_elements = struct.unpack('i', br.read(4))[0]
                        Li[l].element_values = [[None] * len(Li[l].element_types)] * num_elements
                    SStat[1] = len(Li[l].element_values)
                    if Version >= 191:
                        Li[l].element_size = struct.unpack('i', br.read(4))[0]
                    # Iterate through list elements
                    len_le = len(Li[l].element_values)
                    for e in range(len_le):
                        len_lef = len(Li[l].element_values[e])
                        print(f"Process category {e} of {len_le}, entries: {len_lef}")
                        for f in range(len_lef):
                            Li[l].element_values[e][f] = read_value(br, Li[l].element_types[f])
                            # Handle "ID" field
                            if Li[l].element_fields[f] == "ID":
                                idtest = int(Li[l].element_values[e][f])
                                SStat[2] = idtest
                                if l == 0:
                                    if idtest not in addonIndex:
                                        addonIndex[idtest] = e
                                    else:
                                        print(f"Error: Found duplicate Addon id: {idtest}")
                                        addonIndex[idtest] = e
        else:
            print(f"No corresponding configuration file found!\nVersion: {Version}\nPattern: configs/PW_*_v{Version}.cfg")
    return Li

if __name__ == '__main__':
    data = Load('elements.data')
    for elist in data:
        with open(f"{elist.list_name}.json", 'w') as fp:
            json.dump(elist.to_dict(), fp, indent=2)