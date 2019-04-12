import platform
import sys

version = sys.version_info
minor = version.minor
major = version.major
architecture = platform.architecture()[0][:2]
ver = str(major) + str(minor)
arch = '32' if int(architecture) == 32 else '_amd64'

print("Shapely-1.6.4.post1-cp%s-cp37m-win%s.whl" % (ver, arch))
