import csv
import io
import sys

class ConfigFile:
    def __init__(self, filename):
        self.sections = {}   # string -> dictionary

        current_dict = None
        with open(filename, 'r') as f:
            try:
                linenum = 0
                for line in f:
                    linenum += 1
                    line = line.strip()

                    if (len(line) == 0):
                        continue

                    # New section e.g. '[Section]'
                    if line[0] == '[' and len(line) > 1:
                        section_name = line[1:line.find(']')]
                        if section_name in self.sections:
                            print("%d: Duplicate section_name '%s'" %
                                    (linenum, section_name))
                        else:
                            self.sections[section_name] = {}

                        current_dict = self.sections[section_name]
                    elif current_dict is not None:
                        # Split key=value
                        split = line.find('=')
                        if split == -1:
                            print("%d: Not a key-value pair '%s'" %
                                    (linenum, line))
                            continue

                        key = line[:split]
                        value = line[split+1:]

                        if key in current_dict:
                            print("%d: Duplicate key '%s'" % (linenum, key))

                        current_dict[key] = value
                    else:
                        print("%d: Not part of a section '%s'" %
                                (linenum, line))
            except:
                print("%d: Runtime exception" % linenum)
                raise

    def get_value(self, section_name, key):
        if section_name in self.sections and key in self.sections[section_name]:
            return self.sections[section_name][key]
        return None

def parse_int(s):
    # Handle strings of both forms 1234 and 0x1234
    try:
        if s.startswith("0x"):
            return int(s[2:], 16)
        else:
            return int(s)
    except ValueError:
        return None

class DcfObject:
    def __init__(self, address):
        self.address = address
        self.values = {}        # string -> value
        self.children = {}      # int -> DcfObject
        self.name = None
        self.rawvalue = None
        self.value = None
        self.unit = None
        self.llimit = None
        self.hlimit = None
        self.scale = None
        self.access = None

class DcfFile:
    def __init__(self, filename=None):
        self.objects = {}       # string -> {int -> DcfObject}

        if filename is None:
            return

        self.config = ConfigFile(filename)
        # Enumerate objects listed in sections e.g. "[ManufacturerObjects]"
        for section_name in self.config.sections:
            section = self.config.sections[section_name]
            if section_name.endswith('Objects'):
                objtype = section_name[:section_name.find('Objects')]
                self.objects[objtype] = {}

                # Parse all lines of form e.g. "1=0x1000"
                for key in section:
                    if parse_int(key) is not None:
                        address = parse_int(section[key])
                        self.objects[objtype][address] = DcfObject(address)

        # Read parameters for each object
        for section_name in self.config.sections:
            # Try to parse [XXXX] or [XXXXsubY]
            split = section_name.find('sub')
            if split == -1:
                split = len(section_name)
            try:
                x = int(section_name[:split], 16)
            except ValueError:
                continue

            try:
                y = int(section_name[split+3:], 16)
            except ValueError:
                y = None

            obj = self.find_object(x)
            if obj is None:
                print("%d: Couldn't find object '%s'" % (linenum, section_name))
                continue
            if y is not None and y not in obj.children:
                obj.children[y] = DcfObject(y)
                obj = obj.children[y]

            obj.name = self.config.get_value(section_name, 'ParameterName')
            obj.rawvalue = self.config.get_value(section_name, 'ParameterValue')
            obj.unit = self.config.get_value(section_name, ';SEVCONFIELD UNITS')
            obj.llimit = self.config.get_value(section_name, 'LowLimit')
            obj.hlimit = self.config.get_value(section_name, 'HighLimit')
            obj.scale = self.config.get_value(section_name, ';SEVCONFIELD SCALING')
            obj.access = self.config.get_value(section_name, 'AccessType')

            if obj.rawvalue is not None:
                obj.value = parse_int(obj.rawvalue)
                if obj.value is None:
                    obj.value = obj.rawvalue
                elif obj.scale is not None:
                    obj.value *= float(obj.scale)


    def find_object(self, address):
        for objtype in self.objects:
            if address in self.objects[objtype]:
                return self.objects[objtype][address]
        return None

    def to_csv(self, filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Object type', 'Address', 'Subaddress', 'Name',
                'Value', 'Unit', 'Raw value', 'Scale',
                'Low limit', 'High limit', 'Access'])
            for objtype in sorted(self.objects.keys()):
                for address in sorted(self.objects[objtype].keys()):
                    parentobj = self.objects[objtype][address]
                    objs = [parentobj]
                    objs += [parentobj.children[sub]
                             for sub in sorted(parentobj.children.keys())]

                    for obj in objs:
                        subaddress = None
                        if obj.address != address:
                            subaddress = hex(obj.address)
                        writer.writerow([objtype, hex(address), subaddress,
                            obj.name, obj.value, obj.unit, obj.rawvalue,
                            obj.scale, obj.llimit, obj.hlimit, obj.access])

    def to_diff(self, other, filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Object type', 'Address', 'Subaddress', 'Name',
                'Left value', 'Unit', 'Raw value', 'Scale',
                'Low limit', 'High limit', 'Access',
                'Right value', 'Unit', 'Raw value', 'Scale',
                'Low limit', 'High limit', 'Access'])
            # Assuming both have the same basic object types
            # i.e. MandatoryObjects, ManufacturerObjects, and OptionalObjects
            for objtype in sorted(self.objects.keys()):
                laddresses = set(self.objects[objtype].keys())
                raddresses = set(other.objects[objtype].keys())
                for address in sorted(laddresses.union(raddresses)):
                    lparentobj = (self.objects[objtype][address]
                            if address in self.objects[objtype]
                            else DcfObject(address))
                    lsubaddresses = set(lparentobj.children.keys())
                    lobjs = [lparentobj]

                    rparentobj = (other.objects[objtype][address]
                            if address in other.objects[objtype]
                            else DcfObject(address))
                    rsubaddresses = set(rparentobj.children.keys())
                    robjs = [rparentobj]

                    for sub in sorted(lsubaddresses.union(rsubaddresses)):
                        lobjs.append(lparentobj.children[sub]
                                if sub in lparentobj.children
                                else DcfObject(sub))
                        robjs.append(rparentobj.children[sub]
                                if sub in rparentobj.children
                                else DcfObject(sub))

                    for lobj, robj in zip(lobjs, robjs):
                        name = lobj.name if lobj.name is not None else robj.name
                        subaddress = None
                        if lobj.address != address:
                            subaddress = hex(lobj.address)
                        if (lobj.value != robj.value or
                                lobj.rawvalue != robj.rawvalue or
                                lobj.unit != robj.unit or
                                lobj.scale != robj.scale or
                                lobj.llimit != robj.llimit or
                                lobj.hlimit != robj.hlimit or
                                lobj.access != robj.access or
                                len(lobj.children) > 0 or
                                len(robj.children) > 0):
                            writer.writerow([objtype, hex(address), subaddress,
                                name,
                                lobj.value, lobj.unit, lobj.rawvalue,
                                lobj.scale, lobj.llimit, lobj.hlimit,
                                lobj.access,
                                robj.value, robj.unit, robj.rawvalue,
                                robj.scale, robj.llimit, robj.hlimit,
                                robj.access])

def main():
    if len(sys.argv) != 3:
        print("Usage: dcfparser.py <in.dcf> <out.csv>")
        sys.exit(1)
    dcf = DcfFile(sys.argv[1])
    dcf.to_csv(sys.argv[2])

if __name__ == '__main__':
    main()
