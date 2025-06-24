#!/usr/bin/env python

import binascii
import enc
import sys
from subprocess import call
import datetime
import os
import hashlib
import  ConfigParser
import getpass
import qrcode
import csv
from os.path import join
import shutil

DEFAULT_DEPLOY_VERSION = 'elmer.4' # Set here the default version to deploy

PROJECT = 1 # 0 for IRC-SPHERE

DEVICE_OFFSET_GATEWAY_F = 1
DEVICE_OFFSET_GATEWAY_G = 64
DEVICE_OFFSET_ENVIRONMENTAL = 128
DEVICE_OFFSET_WEARABLE = 192

MEM_OFFSET_CONTIKI = "0x01FF88"
MEM_OFFSET_CONTIKI_END = "0x01FFA6"
MEM_OFFSET_GATEWAY_G = "0xAFE0"
MEM_OFFSET_GATEWAY_G_END = "0xAFFE"
MEM_OFFSET_WEARABLE = "0xDFE0"
MEM_OFFSET_WEARABLE_END = "0xDFFE"

TEST_NETWORK_ID_MIN = 250
TEST_NETWORK_ID_MAX = 254


LABELS_PAPER_SIZE = 1 # 5x13 (new)
#LABELS_PAPER_SIZE = 2 # 4x10 (old)

def mac2ipv6(mac):
    # only accept MACs not separated by a colon
    m = ':'.join(mac[i:i+2] for i in range(0,len(mac),2))
    parts = m.split(":")

    parts[0] = "%x" % (int(parts[0], 16) ^ 2)

    # format output
    ipv6Parts = []
    for i in range(0, len(parts), 2):
        ipv6Parts.append("".join(parts[i:i+2]))
    ipv6 = "fd00::%s" % (':'.join('0' if i.count('0')==4 else i.lstrip('0') for i in ipv6Parts))
    return ipv6

def open_keyfile(password):
    with open ("ckeys.hash", "r") as f:
      hash=f.readlines()
    f.close()
    with open("ckeys", 'rb') as in_file:
        keys = enc.decrypt(in_file, password)
        if  hashlib.sha1(keys).hexdigest() != hash[0]:
            return "";
        else:
            return binascii.hexlify(keys)
    in_file.close()

def get_key(networkID,keys_hex):
    if TEST_NETWORK_ID_MIN <= networkID <= TEST_NETWORK_ID_MAX:
        # A non-secure test network; just use repeated network ID as the key
        return "{:02x}".format(networkID) * 16
    # A secure network; use the key from the file
    return keys_hex[(networkID*16)*2:((networkID+1)*16)*2]

def make_qrcode(directory_qr, lf, addr, device_type, count, c):
    qr=qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    if device_type == "W":
	    m = ':'.join(addr[i:i+2] for i in range(0,len(addr),2))
	    qr.add_data(m)
    else:
	    qr.add_data(mac2ipv6(addr))
    qr.make(fit=True)
    img=qr.make_image()
    qr_filename = device_type + "%.2d" % (c) + "_" + addr+".png"
    img.save(join(directory_qr, qr_filename))
    lf.write("\\begin{tikzpicture}[remember picture,overlay]\n")

    if LABELS_PAPER_SIZE == 1:
      col = count // 13
      row = count % 13
      x = 1.5+4.2*col
      y = 1.6+2.25*row

    if LABELS_PAPER_SIZE == 2:
      col = count // 10
      row = count % 10
      x = 2.5+5.1*col
      y = 2.8+2.7*row


    lf.write("\\node[xshift="+"%.3f" % x +"cm,yshift=-"+"%.3f" % y +"cm] at (current page.north west) {\\includegraphics[width=2cm]{" + qr_filename + "}};\n")
    if device_type == "W":
        lf.write("\\node[xshift="+"%.3f" % (x+1.5) +"cm,yshift=-"+"%.3f" % (y+0.3) +"cm] at (current page.north west) {" + device_type + "%s" % (addr[-2:].upper()) + "};\n")
        lf.write("\\node[xshift="+"%.3f" % (x+1.5) +"cm,yshift=-"+"%.3f" % (y-0.3) +"cm] at (current page.north west) {" + chr(ord(addr[-1:].upper()) + 17) + "};\n")
    else:
        lf.write("\\node[xshift="+"%.3f" % (x+1.5) +"cm,yshift=-"+"%.3f" % y +"cm] at (current page.north west) {" + device_type + "%s" % (addr[-2:].upper()) + "};\n")
    lf.write("\\end{tikzpicture}\n")


def make_ieee_addr(project, network, device, be = True):
    if be == True:
        IEEE802154_addr = "00124b0000" + "%.2x" % (project) + "%.2x" % (network) + "%.2x" % (device) # Big-endian
    else:
        IEEE802154_addr = "%.2x" % (device) + "%.2x" % (network) + "%.2x" % (project) + "00004b1200" # Little-endian
    return IEEE802154_addr

def make_ble_addr(project, network, device, be = True):
    if be == True:
        BLE_addr = "a0e6f8" + "%.2x" % (project) + "%.2x" % (network) + "%.2x" % (device) # Big-endian
    else:
        BLE_addr = "%.2x" % (device) + "%.2x" % (network) + "%.2x" % (project) + "f8e6a0" # Little-endian
    return BLE_addr

def make_image(network, keys, ieee_addr_le, ble_addr_le, offset, offsetend, filename, directory, addr, device_type, subtype, count, tc):
    with open("key.bin", 'wb') as f:
        f.write(binascii.unhexlify(get_key(network,keys)))
        f.write(binascii.unhexlify(ieee_addr_le))
        f.write(binascii.unhexlify(ble_addr_le))
    f.close()
    call(["srec_cat", "key.bin", "-binary", "-offset", offset, join(directory_firmware, filename), "-intel", "-exclude", offset, offsetend, "-o", join(directory, device_type + "%.2d" % (tc) + subtype + "_" + addr+".hex"), "-intel"])
    os.remove("key.bin")
 
###########################################################################################

if not os.path.isfile('ckeys'):
    print("Not installed. Run install.py first.")
    sys.exit(1)

# Input parameters
if len(sys.argv) < 2:
    print("Incorrect input parameters. Set HID.")
    sys.exit(1)

config_file = sys.argv[1] + ".cfg"

if os.path.isfile(join("config", config_file)) == False:
    print("Configuration file does not exist.")
    sys.exit(1)

config = ConfigParser.ConfigParser()
config.readfp(open(join("config", config_file)))

total_gateways = int(config.get("DEFAULT", "total_gateways"))
if total_gateways < 0 or total_gateways > 62:
    print("Incorrect number of gateways. Use [0-62].")
    sys.exit(1)

total_environmental = int(config.get("DEFAULT", "total_environmental"))
if total_environmental < 0 or total_environmental > 64:
    print("Incorrect number of environmental sensors. Use [0-64].")
    sys.exit(1)

total_wearables = int(config.get("DEFAULT", "total_wearables"))
if total_wearables < 0 or total_wearables > 64:
    print("Incorrect number of wearables. Use [0-64].")
    sys.exit(1)

tsch_type = config.get("DEFAULT", "tsch")

# Deploy Version
try:
	deploy_version = config.get("DEFAULT", "version")
except ConfigParser.NoOptionError:
	deploy_version = DEFAULT_DEPLOY_VERSION
	print("No explicit system version specified. Using default: " + deploy_version)
else:
	print("Using system version: " + deploy_version)
directory_firmware = join("firmware", deploy_version)
if not os.path.exists(directory_firmware):
    print("Cannot find system version: " + deploy_version)
    sys.exit(1)

## Important note:
## - Deploy version 'dangermouse.41' and 'dangermouse.42' uses TI-RTOS firmware for Root Gateway G with address DEVICE_OFFSET_GATEWAY_G
## - Newer deploy versions use Contiki Firmware for Root Gateway G with address N+1 (where N is the total number of gateways)
if (deploy_version == 'dangermouse.41' or deploy_version == 'dangermouse.42'):
	RG_G_Contiki = 0
	RG_G_Addr = DEVICE_OFFSET_GATEWAY_G
else:
	RG_G_Contiki = 1
	RG_G_Addr = total_gateways + 2

Wearable_Contiki = 0
Wearable_Firmware_Filename = "SPW2_full.hex"
if (deploy_version == 'cng-sphere'):
	MEM_OFFSET_WEARABLE = MEM_OFFSET_CONTIKI
	MEM_OFFSET_WEARABLE_END = MEM_OFFSET_CONTIKI_END
	Wearable_Firmware_Filename = "sphere-wearable.hex"
	Wearable_Contiki = 1

# convert house ID to network ID
network = -1
house = int(config.get("DEFAULT", "house_id"))
house_string = "%.4d" % (house)
with open('sphere_network_id.csv', 'rb') as fc:
    reader = csv.reader(fc, delimiter=',')
    for row in reader:
         if row[1] == house_string:
             if row[2] == "0":
                 print "House ID not allocated."
                 sys.exit(1)
             if row[3] == "0":
                 print "House ID not active."
                 sys.exit(1)
             network = int(row[0])

if network == -1:
    print("House ID not registered in 'sphere_network_id.csv'.")
    sys.exit(-1)

if TEST_NETWORK_ID_MIN <= network <= TEST_NETWORK_ID_MAX:
    keys = ""
else:
    # Unlock key file
    password = getpass.getpass()
    keys = open_keyfile(password)
    if keys == "":
        print("Wrong password.")
        sys.exit(1)

# Make the directory structure
if not os.path.exists("out"):
    os.makedirs("out")
if not os.path.exists("firmware"):
    os.makedirs("firmware")

directory = join("out", house_string)
try:
  if os.path.exists(directory):
    shutil.rmtree(directory)
finally:
  os.makedirs(directory)

af = open(join(directory, "addresses.txt"), "w")

directory_img = join(directory, "img")
if not os.path.exists(directory_img):
    os.makedirs(directory_img)
directory_qr = join(directory, "qr")
if not os.path.exists(directory_qr):
    os.makedirs(directory_qr)

lf = open(join(directory_qr, "labels.tex"), "w")
lf.write("\\documentclass[12pt, a4paper]{article}\n")
lf.write("\\usepackage{tikz}\n")
lf.write("\\begin{document}\n")
lf.write("\\pagenumbering{gobble}")

print("SPHERE Deployment Manager - Report")
print("--------------------------------------------")
print("House ID: " + house_string)
print("Network ID: " + "%d" % (network))
print("Date: " + datetime.date.today().strftime('%Y-%m-%d'))


# GATEWAYS
call(["srec_cat", join(directory_firmware, "G2.hex"), "-intel", join(directory_firmware, "G2Stack.hex"), "-intel", "-o", join(directory_firmware, "G2_full.hex"), "-intel"])   

print("Total Gateways: " + str(total_gateways))

# Root gateway F
device_count = 0
device_f = DEVICE_OFFSET_GATEWAY_F

label_addr = make_ieee_addr(PROJECT, network, device_f)

BLE_addr_le = make_ble_addr(PROJECT, network, device_f, False)
IEEE802154_addr_le =  make_ieee_addr(PROJECT, network, device_f, False)

make_image(network, keys, IEEE802154_addr_le, BLE_addr_le, MEM_OFFSET_CONTIKI, MEM_OFFSET_CONTIKI_END, join(tsch_type,"br.hex"), directory_img, label_addr, "G", "F", device_count,1)

af.write(label_addr + "\n")

make_qrcode(directory_qr, lf, label_addr, "G", device_count, 1)

print("[Device: " + "%.3d" % (device_f) + "] Image created. Root Gateway (F): " + label_addr)    


# Root gateway G
device_g = RG_G_Addr

label_addr = make_ieee_addr(PROJECT, network, device_g)

BLE_addr_le = make_ble_addr(PROJECT, network, device_g, False)
IEEE802154_addr_le =  make_ieee_addr(PROJECT, network, device_g, False)

if RG_G_Contiki == 0:
	make_image(network, keys, IEEE802154_addr_le, BLE_addr_le, MEM_OFFSET_GATEWAY_G, MEM_OFFSET_GATEWAY_G_END, "G2_full.hex", directory_img, label_addr, "G", "G", device_count,1)
else:
	make_image(network, keys, IEEE802154_addr_le, BLE_addr_le, MEM_OFFSET_CONTIKI, MEM_OFFSET_CONTIKI_END, join(tsch_type,"br.hex"), directory_img, label_addr, "G", "G", device_count,1)

af.write(label_addr + "\n")

print("[Device: " + "%.3d" % (device_g) + "] Image created. Root Gateway (G): " + label_addr)    


# Other gateways
for gateway_count in range(1,total_gateways):
    device_count = device_count + 1
    # Other gateways F
    device_f = DEVICE_OFFSET_GATEWAY_F + gateway_count + 1

    label_addr = make_ieee_addr(PROJECT, network, device_f)

    BLE_addr_le = make_ble_addr(PROJECT, network, device_f, False)
    IEEE802154_addr_le =  make_ieee_addr(PROJECT, network, device_f, False)

    make_image(network, keys, IEEE802154_addr_le, BLE_addr_le, MEM_OFFSET_CONTIKI, MEM_OFFSET_CONTIKI_END, join(tsch_type,"spg.hex"), directory_img, label_addr, "G", "F", device_count, gateway_count+1)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "G", device_count, gateway_count+1)

    print("[Device: " + "%.3d" % (device_f) + "] Image created. Gateway (F): " + label_addr)


    # Other gateways G
    device_g = DEVICE_OFFSET_GATEWAY_G + gateway_count + 1

    label_addr = make_ieee_addr(PROJECT, network, device_g)

    BLE_addr_le = make_ble_addr(PROJECT, network, device_g, False)
    IEEE802154_addr_le =  make_ieee_addr(PROJECT, network, device_g, False)

    make_image(network, keys, IEEE802154_addr_le, BLE_addr_le, MEM_OFFSET_GATEWAY_G, MEM_OFFSET_GATEWAY_G_END, "G2_full.hex", directory_img, label_addr, "G", "G", device_count, gateway_count+1)

    af.write(label_addr + "\n")

    print("[Device: " + "%.3d" % (device_g) + "] Image created. Gateway (G): " + label_addr)    

# ENVIRONMENTAL SENSORS
print("Total Environmental: " + str(total_environmental))
for env_count in range(0,total_environmental):
    device_count = device_count + 1

    device = DEVICE_OFFSET_ENVIRONMENTAL + env_count

    label_addr = make_ieee_addr(PROJECT, network, device)

    BLE_addr_le = make_ble_addr(PROJECT, network, device, False)
    IEEE802154_addr_le =  make_ieee_addr(PROJECT, network, device, False)

    make_image(network, keys, IEEE802154_addr_le, BLE_addr_le, MEM_OFFSET_CONTIKI, MEM_OFFSET_CONTIKI_END, join(tsch_type,"spes.hex"), directory_img, label_addr, "E", "", device_count, env_count)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "E", device_count, env_count)

    print("[Device: " + "%.3d" % (device) + "] Image created. Environmental: " + label_addr)

    make_image(network, keys, IEEE802154_addr_le, BLE_addr_le, MEM_OFFSET_CONTIKI, MEM_OFFSET_CONTIKI_END, join(tsch_type, "spwater.hex"), directory_img, label_addr, "AQ", "", device_count, env_count)

    print("[Device: " + "%.3d" % (device) + "] Image created. Water sensor: " + label_addr)


# WEARABLES
if (Wearable_Contiki == 0):
	call(["srec_cat", join(directory_firmware, "SPW2.hex"), "-intel", join(directory_firmware, "SPW2Stack.hex"), "-intel", "-o", join(directory_firmware, Wearable_Firmware_Filename), "-intel"])   

print("Total Wearables: " + str(total_wearables))
for wearable_count in range(0,total_wearables):
    device_count = device_count + 1

    device = DEVICE_OFFSET_WEARABLE + wearable_count

    label_addr = make_ble_addr(PROJECT, network, device)

    BLE_addr_le = make_ble_addr(PROJECT, network, device, False)
    IEEE802154_addr_le =  make_ieee_addr(PROJECT, network, device, False)

    make_image(network, keys, IEEE802154_addr_le, BLE_addr_le, MEM_OFFSET_WEARABLE, MEM_OFFSET_WEARABLE_END, Wearable_Firmware_Filename, directory_img, label_addr, "W", "", device_count, wearable_count)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "W", device_count, wearable_count)

    print("[Device: " + "%.3d" % (device) + "] Image created. Wearable: " + label_addr)    


af.close()
lf.write("\\end{document}\n")
lf.close()

print("Creating labels..")
os.chdir(join("out", house_string,"qr"))
with open(os.devnull, "w") as fnull:
    result = call(["pdflatex", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull)
    result = call(["pdflatex", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull)   
print("Labels written in labels.pdf")
