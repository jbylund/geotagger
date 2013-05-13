#!/usr/bin/python
import os, argparse, math, sys, subprocess

class planet:
    def __init__(self,radius):
        self.radius = radius

    def radius(self):
        return self.radius

class row:
    def __init__(self,rowstring):
        row_contents  = rowstring.split(",")
        self.city     = row_contents[0].rstrip('"').lstrip('"')
        self.state    = row_contents[1]
        self.position = phi_psi(row_contents[2],row_contents[3])
        self.timezone = row_contents[4]
        self.dst      = row_contents[5]

    def __repr__(self):
        return self.city + ", " + self.state + " " + str(self.position)

class phi_psi:
    def __init__(self,phi,psi):
        self.phi = math.radians(float(phi))
        self.psi = math.radians(float(psi))

    def longitude(self):
        return self.phi

    def latitude(self):
        return self.psi

    def __repr__(self):
        return "(" + `round(math.degrees(self.phi),2)` + ", " + `round(math.degrees(self.psi),2)` + ")"

def great_circle_distance(p1,p2):
    dlong = p2.longitude() - p1.longitude()
    dlat = p2.latitude() - p1.latitude()
    a = (math.sin(dlat / 2.0))**2 + math.cos(p1.latitude()) * math.cos(p2.latitude()) * (math.sin(dlong / 2.0))**2
    if(a < 1):
        c = 2 * math.asin(math.sqrt(a))
    else:
        c = 2 * math.asin(1)        
    dist = earth.radius * c
    return dist

def geotag(p1,location_database):
    if(None == p1):
        return None
    x_frac = (p1.phi - min_x) / (max_x - min_x)
    y_frac = (p1.psi - min_y) / (max_y - min_y)
    x_guess = int(round(x_frac * divisions))
    y_guess = int(round(y_frac * divisions))
    best_distance = sys.float_info.max
    best_location = None
    for x in xrange(max(0,x_guess-1),min(x_guess+1+1,divisions)):
        for y in xrange(max(0,y_guess-1),min(y_guess+1+1,divisions)):
            for irow in location_database[x][y]:
                this_distance = great_circle_distance(p1,irow.position)
                if(this_distance < best_distance):
                    best_distance = this_distance
                    best_location = irow
    return best_location

def init_image_extensions(valid_image_extensions):
    valid_image_extensions.add("arw")
    valid_image_extensions.add("cr2")
    valid_image_extensions.add("crw")
    valid_image_extensions.add("dng")
    valid_image_extensions.add("jpeg")
    valid_image_extensions.add("jpg")
    valid_image_extensions.add("nef")
    valid_image_extensions.add("orf")
    valid_image_extensions.add("raw")
    valid_image_extensions.add("sr2")
    valid_image_extensions.add("srw")

def geotag_file(ifile,location_database):
    file_phi_psi = get_lat_long_file(ifile)
    file_location = geotag(file_phi_psi,location_database)
    if(file_location != None):
        subprocess.call(["exiftool","-v", ifile, "-City=\"" + file_location.city+"\"","-State=\"" + file_location.state + "\""],stderr=dev_null)

def get_lat_long_file(ifile):
    gps_array = subprocess.check_output(["exiftool", ifile, "-GPSPosition"],stderr=dev_null).rstrip().split(":")
    if(1 == len(gps_array)):
        return None
    latitude = string_to_decimal(gps_array[1].split(",")[0])
    longitude = string_to_decimal(gps_array[1].split(",")[1])
    return phi_psi(latitude,longitude)

def string_to_decimal(angle_string):
    angle_array = angle_string.split()
    ans = int(angle_array[0]) + int(angle_array[2].rstrip("'"))/60.0 + float(angle_array[3].rstrip('"'))/3600.0
    if("S" == angle_array[-1] or "W" == angle_array[-1]):
        return -1*ans
    return ans

dev_null = open('/dev/null', 'w')
earth = planet(6368)
parser = argparse.ArgumentParser()
parser.add_argument('--recurse', action='store_true', help='Recurse into subdirectories')
args = parser.parse_args()

# set up valid image extensions
valid_image_extensions = set()
init_image_extensions(valid_image_extensions)

# set up the list of files
files_array = list()
for path,subdirs,files in os.walk("."):
    if(path != "." and not args.recurse):
        break
    for ifile in files:
        extension = ifile.lower().split(".")[-1]
        if(extension in valid_image_extensions):
            files_array.append("/".join([path,ifile]))

# set up the min and max bounding box
min_x = 5 * math.pi
max_x = -5 * math.pi
min_y = 5 * math.pi
max_y = -5 * math.pi

# read in the zip database
zip_code_database = list()
zip_code_file = open("zip_database.csv", 'r')
for rowstring in zip_code_file:
    rowstring = rowstring.rstrip()
    if(0 == len(rowstring)):
        continue
    if("#" == rowstring[0]):
        continue
    zip_code_database.append(row(rowstring))
    min_x = min(min_x,zip_code_database[-1].position.phi)
    max_x = max(max_x,zip_code_database[-1].position.phi)
    min_y = min(min_y,zip_code_database[-1].position.psi)
    max_y = max(max_y,zip_code_database[-1].position.psi)
zip_code_file.close()

# make a cell table
zip_code_dict = list()
divisions = 50
for i in xrange(divisions):
    zip_code_dict.append(list())
    for j in xrange(divisions):
        zip_code_dict[i].append(list())

# put the zip database into "cells"
for j in xrange(len(zip_code_database)):
    i = zip_code_database[j]
    x_frac = (i.position.phi - min_x) / (max_x - min_x)
    y_frac = (i.position.psi - min_y) / (max_y - min_y)
    x = min(int(round(x_frac * divisions)),divisions - 1)
    y = min(int(round(y_frac * divisions)),divisions - 1)
    zip_code_dict[x][y].append(i)

for ifile in files_array:
    print "Processing:",ifile," ..."
    geotag_file(ifile,zip_code_dict)

dev_null.close()
