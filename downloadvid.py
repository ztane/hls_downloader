#!/usr/bin/python
import os
import shlex
from urllib.parse import urljoin

import requests
from Crypto.Cipher import AES
from pkcs7 import PKCS7Encoder


def validate_and_strip_pkcs7(pt, block_size):
    padding_size = pt[-1]
    if padding_size > block_size:
        raise ValueError('Padding too long')

    padding = pt[-padding_size:]
    if padding != pt[-1:] * padding_size:
        raise ValueError('Invalid padding')

    return pt[:-padding_size]


def parse_curl_command(prompt):
    command = input('{}> '.format(prompt))
    components = shlex.split(command)
    if components.pop(0) != 'curl':
        raise ValueError('The command is invalid')

    url = components.pop(0)
    if not url.startswith('http'):
        raise ValueError('The command is invalid')

    headers = []
    while components:
        c = components.pop(0)
        if c == '--compressed':
            continue
        if c != '-H':
            raise ValueError('The command is invalid (unexpected {})'.format(c))
        header = components.pop(0)
        name, value = header.split(': ', 1)
        headers.append((name, value))

    return url, headers


m3u8_url, headers = parse_curl_command('Enter m3u8 curl')

contents = requests.get(m3u8_url, headers=dict(headers))
m3u8_contents = contents.text
lines = m3u8_contents.splitlines()
for i in lines:
    if i.startswith('#EXT-X-KEY'):
        key_uri = i.split('"')[1]

print(key_uri)
sauth_url, sauth_headers = parse_curl_command('Enter key curl')
key_response = requests.get(key_uri, headers=dict(sauth_headers))
key = key_response.content
print('Using key {}'.format(key.hex()))

filtered_urls = [i for i in lines if not i.startswith('#')]
with open('output.m2v', 'wb') as f:
    for n, i in enumerate(filtered_urls):
        print('downloading part {}/{}'.format(n + 1, len(filtered_urls)))

        joined = urljoin(m3u8_url, i)
        print('Url', joined)
        r = requests.get(joined, headers=dict(headers))
        cipher = AES.new(key, AES.MODE_CBC, (n).to_bytes(16, 'big'))
        f.write(validate_and_strip_pkcs7(cipher.decrypt(r.content), 16))
