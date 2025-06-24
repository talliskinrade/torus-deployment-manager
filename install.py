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

KEY_NUM = 256
KEY_SIZE = 16

def gen_keyfile(in_file,password):
  with open("ckeys", 'wb') as keyfile:
    keys = enc.encrypt(in_file,keyfile,password)
  keyfile.close()

def get_hash(password):
  with open("ckeys", 'rb') as keyfile:
    keys = enc.decrypt(keyfile,password)
    hash = hashlib.sha1(keys).hexdigest()
  keyfile.close()
  return hash

def open_keyfile(password,hash):
    with open("ckeys", 'rb') as keyfile:
        keys = enc.decrypt(keyfile, password)
        ok = (hashlib.sha1(keys).hexdigest() == hash)
    keyfile.close()
    return ok

###########################################################################################

print("SPHERE Deployment Manager - Installation Script")

if (os.path.isfile('ckeys')):
  print("Key file 'ckeys' already exists. Manually delete it to reinstall.")
  sys.exit(1)

print("Set password for key file.")
password = getpass.getpass()

with open('tmp', 'wb') as f:
  f.write(os.urandom(KEY_NUM*KEY_SIZE))
f.close()

with open('tmp', 'rb') as f:
  gen_keyfile(f,password)
f.close()

os.remove('tmp')

with open('ckeys.hash', 'w') as f:
  hash = get_hash(password)
  f.write(hash)
f.close()

print("Type password again.")
password = getpass.getpass()
ok = open_keyfile(password,hash)

if(not ok):
  print("Wrong password. Try again.")
  os.remove('ckeys')
  os.remove('ckeys.hash')
  sys.exit(1)

with open("sphere_network_id.csv", 'w') as f:
  f.write("Network ID (NID), House ID (HID), Allocated, Active\n")
  for i in range(KEY_NUM):
    f.write(str(i) + ",-1,,\n")

print("Installation Complete.")
