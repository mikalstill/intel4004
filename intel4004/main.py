import sys

from intel4004 import emulator


em = emulator.Intel4004()

while l := sys.stdin.readline():
    print(l)
