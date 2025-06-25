from hashlib import md5
from Cryptodome.Cipher import AES
from Cryptodome import Random

def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = b''
    password = password.encode()
    while len(d) < key_length + iv_length:

        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

def encrypt(in_file, out_file, password, key_length=32):
    bs = AES.block_size
    salt = Random.new().read(bs - len('Salted__'))
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    out_file.write(b'Salted__' + salt)
    chunk = in_file.read(256 * bs)
    out_file.write(cipher.encrypt(chunk))

def decrypt(in_file, password, key_length=32):
    bs = AES.block_size
    salt = in_file.read(bs)[len('Salted__'):]
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    chunk = cipher.decrypt(in_file.read(256 * bs))
    return chunk