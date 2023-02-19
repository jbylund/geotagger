#!/usr/bin/python
import os, argparse, math, sys, subprocess, operator
from pygeocoder import Geocoder
from geopy import geocoders

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
        return f"{self.city}, {self.state} {str(self.position)}"

class phi_psi:
    def __init__(self,phi,psi):
        self.phi = math.radians(float(phi))
        self.psi = math.radians(float(psi))

    def latitude(self):
        return self.phi

    def longitude(self):
        return self.psi

    def __repr__(self):
        return "(" + `round(math.degrees(self.phi),2)` + ", " + `round(math.degrees(self.psi),2)` + ")"

def great_circle_distance(p1,p2):
    dlong = p2.latitude() - p1.latitude()
    dlat = p2.longitude() - p1.longitude()
    a = (math.sin(dlat / 2.0))**2 + math.cos(p1.longitude()) * math.cos(p2.longitude()) * (math.sin(dlong / 2.0))**2
    c = 2 * math.asin(math.sqrt(a)) if (a < 1) else 2 * math.asin(1)
    return earth.radius * c

def geotag(p1,location_database):
    if p1 is None:
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
    print "\nLocal:"
    file_phi_psi = get_lat_long_file(ifile)
    file_location = geotag(file_phi_psi,location_database)
    if(file_location != None):
        subprocess.call(["exiftool","-q", "-q", ifile, "-City=\"" + file_location.city+"\"","-State=\"" + file_location.state + "\""],stderr=dev_null)
        print file_location.city, file_location.state

def google_geotag_file(ifile):
    print "\nGoogle:"
    file_phi_psi = get_lat_long_file(ifile)
    location = Geocoder.reverse_geocode(math.degrees(file_phi_psi.latitude()), math.degrees(file_phi_psi.longitude()))
    admin = "administrative_area_level_"
    location_attributes = list()
    location_attributes.append(["country",           "Country          ","-country="])
    location_attributes.append([admin + "1",         "State            ","-state="])
    location_attributes.append(["locality",          "City             ","-city="])
    location_attributes.append(["postal_code",       "Zip Code         ", "-Keywords+="])
    location_attributes.append(["neighborhood",      "Neighborhood     ", "-Keywords+="]) # UWS
    location_attributes.append(["political",         "City?            ", ""]) # great falls/uws
    location_attributes.append([admin + "2",         "County           ", ""]) # county
    location_attributes.append([admin + "3",         "District         ", ""]) # district?
    location_attributes.append(["sublocality",       "Sublocality      ", ""]) # manhattan
    location_attributes.append(["airport",           "Airport          ", ""])
    location_attributes.append(["park",              "Park             ", ""])
    location_attributes.append(["natural_feature",   "Natural Feature  ", ""])
    location_attributes.append(["point_of_interest", "Point of Interest", ""])
    location_attributes.append(["street_address",    "Street Address   ", ""])
    location_attributes.append(["route",             "Road             ", ""])
    location_attributes.append(["intersection",      "Intersection     ", ""])
    location_attributes.append(["colloquial_area",   "Colloquial Area  ", ""])
    location_attributes.append(["premise",           "Premise          ", ""])
    location_attributes.append(["subpremise",        "Subpremise       ", ""])

    for i in location_attributes[:5]:
        this_attr = getattr(location[0], i[0])
        if(this_attr != None):
            print i[1], "\t", this_attr

def get_lat_long_file(ifile):
    gps_array = subprocess.check_output(["exiftool", "-q", "-q", ifile, "-GPSPosition"],stderr=dev_null).rstrip().split(":")
    if len(gps_array) == 1:
        return None
    longitude = string_to_decimal(gps_array[1].split(",")[0])
    latitude = string_to_decimal(gps_array[1].split(",")[1])
    return phi_psi(longitude,latitude)

def string_to_decimal(angle_string):
    angle_array = angle_string.split()
    ans = int(angle_array[0]) + int(angle_array[2].rstrip("'"))/60.0 + float(angle_array[3].rstrip('"'))/3600.0
    return -1*ans if angle_array[-1] in ["S", "W"] else ans

####################################################################################################################################
##############  Main   #############################################################################################################
####################################################################################################################################

with open('/dev/null', 'w') as dev_null:
    earth = planet(6368)
    parser = argparse.ArgumentParser()
    parser.add_argument('--recurse', action='store_true', help='Recurse into subdirectories')
    args = parser.parse_args()

    # set up valid image extensions
    valid_image_extensions = set()
    init_image_extensions(valid_image_extensions)

    # set up the list of files
    files_array = []
    for path,subdirs,files in os.walk("."):
        if(path != "." and not args.recurse):
            break
        for ifile in files:
            extension = ifile.lower().split(".")[-1]
            if(extension in valid_image_extensions):
                files_array.append("/".join([path,ifile]))

    # set up the min and max bounding box
    min_x =  5 * math.pi
    max_x = -5 * math.pi
    min_y =  5 * math.pi
    max_y = -5 * math.pi

    # read in the zip database
    zip_code_database = []
    with open("zip_database.csv", 'r') as zip_code_file:
        for rowstring in zip_code_file:
            rowstring = rowstring.rstrip()
            if len(rowstring) == 0:
                continue
            if rowstring[0] == "#":
                continue
            zip_code_database.append(row(rowstring))
            min_x = min(min_x,zip_code_database[-1].position.phi)
            max_x = max(max_x,zip_code_database[-1].position.phi)
            min_y = min(min_y,zip_code_database[-1].position.psi)
            max_y = max(max_y,zip_code_database[-1].position.psi)
    # make a cell table
    zip_code_dict = []
    divisions = 50
    for i in xrange(divisions):
        zip_code_dict.append([])
        for _ in xrange(divisions):
            zip_code_dict[i].append([])

    # put the zip database into "cells"
    for j in xrange(len(zip_code_database)):
        i = zip_code_database[j]
        x_frac = (i.position.phi - min_x) / (max_x - min_x)
        y_frac = (i.position.psi - min_y) / (max_y - min_y)
        x = min(int(round(x_frac * divisions)),divisions - 1)
        y = min(int(round(y_frac * divisions)),divisions - 1)
        zip_code_dict[x][y].append(i)


    for j in xrange(len(zip_code_database)):
        i = zip_code_database[j]
        x_frac = (i.position.phi - min_x) / (max_x - min_x)
        y_frac = (i.position.psi - min_y) / (max_y - min_y)
        x = min(int(round(x_frac * divisions)),divisions - 1)
        y = min(int(round(y_frac * divisions)),divisions - 1)
        zip_code_dict[x][y].append(i)


    # process the files
    for ifile in files_array:
        print "Processing:",ifile," ..."
        geotag_file(ifile,zip_code_dict)
        google_geotag_file(ifile)
        print "\n"

dev_null = open('/dev/null', 'w')
print "Done with", len(files_array), "files."
