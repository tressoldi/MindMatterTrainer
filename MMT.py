# MIND MATTER TRAINER OPEN SOURCE SOFTWARE
# Created by Luca Semenzato; luca.semenzato@unipd.it
# All rights reserved to Patrizio Tressoldi; email: patrizio.tressoldi@unipd.it

# This Software allows to test frequency of 0/1 bits in random choice


import errno
import serial
import binascii
import winsound
import datetime
import configparser
import matplotlib.pyplot as plt
import time
from serial.tools import list_ports
import fnmatch
import os.path
import msvcrt

file_conf = 'Calibration.ini'
file_analysis = 'MindMatterTrainer.csv'
file_plot = 'Plot.png'
file_dir = 'MindMatterTrainer'
version = '1.0.1'

# Default configuration data
# Number of bits/sec from the TrueRNG (>400000 bit/sec)
bit_sample = 16
# Time Interval for data analyses in seconds
int_time = 10
# Time interval for a sample in seconds
sample_time = 1


csv_len = len(fnmatch.filter(os.listdir(os.path.dirname(os.path.realpath(__file__))), '*.csv'))


def mypause(interval):
    manager = plt._pylab_helpers.Gcf.get_active()
    if manager is not None:
        canvas = manager.canvas
        if canvas.figure.stale:
            canvas.draw_idle()

        canvas.start_event_loop(interval)
    else:
        time.sleep(interval)


# Add hash to a file to create an always new file. Hash based on timestamp
def addhashtofile(file):
    import hashlib
    d = str(datetime.datetime.now())
    h = int(hashlib.sha256(d.encode('utf-8')).hexdigest(), 16) % 10**8
    file = str(csv_len) + "_" + file.split('.')[0] + '_' + str(h) + '.' + file.split('.')[1]
    return file


def configsectionmap(section):

    dict1 = {}
    options = config.options(section)
    for option in options:
        # noinspection PyBroadException
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
        except Exception as e1:
            print("Exception! Error: %s" % str(e1))
            dict1[option] = None
    return dict1


# Print our Principal Header
print('============= '+file_dir+' '+version+' ================')
print('==================================================')

config = configparser.ConfigParser()
try:
    # Extract the Variables from the Calibration file
    config.read(file_conf)
except Exception as e:
    print('Can\'t load calibration.ini. Error: %s' % str(e))
    print('Do you have permissions set to read the file?')
    exit(errno.ENOENT)
try:
    # Number of bits/sample from the TrueRNG (>400000 bit/sec)
    bit_sample = int(configsectionmap("Time")['bit_sample'])

    # Time Interval for data analyses in seconds(y)
    int_time = int(configsectionmap("Time")['int_time'])

    # Time Interval for a sample
    sample_time = int(configsectionmap("Time")['sample_time'])

except Exception as e:
    print('Can\'t convert configuration values. Data format error? Error: %s' % str(e))
    print('Do you write the configuration properly?')
    exit(errno.ENOEXEC)

# time delay for each byte pick, as a regular sampling of byte per sec
delay_time = sample_time/(bit_sample / 8)

# byte_sec
byte_sample = bit_sample / 8

# adding hash to out file
csv_len += 1
file_analysis = addhashtofile(file_analysis)
print('Analysis file: %s' % str(file_analysis))
out_file = None
try:
    # Write on "MindMatterTrainer.csv" the output information about the tests
    out_file = open(file_analysis, 'w')
except Exception as e:
            print('Can\'t open %s. Error: %s' % (file_analysis, str(e)))
            exit(errno.ENOENT)

# Create ports variable as dictionary
ports = dict()

# Call list_ports to get com port info
ports_available = list(list_ports.comports())

# Set default of None for com port
rng_com_port = None

# Debug random if rng_com_port is not allowable
debug_rand = False

# Loop on all available ports to find TrueRNG
for temp in ports_available:
    if temp[1].startswith("TrueRNG"):
        print('Found:           ' + str(temp))
        if not rng_com_port:  # always chooses the 1st TrueRNG found
            rng_com_port = str(temp[0])

# Print which port we're using
print('Using com port:  ' + str(rng_com_port))

out_file.write('DEBUG;')
out_file.write('Read;')
out_file.write('Zero count;')
out_file.write('One count;')
out_file.write('Onset time;')
out_file.write('Marker;')
out_file.write('Timestamp')
out_file.write('\n')

dtn = datetime.datetime.now()

print('TimeStamp: %s ' % str(dtn))

# Print General Information
print('==================================================')
print('Interval Time:                      %d seconds' % int_time)
print('One byte read every:                %s seconds' % delay_time)
print('==================================================')

ser = None
# Try to setup and open the comport
try:
    ser = serial.Serial(port=rng_com_port, timeout=10)  # timeout set at 10 seconds in case the read fails
except Exception as e:
    print('Port Not Usable!Error: %s' % str(e))
    print('Do you have permissions set to read port: "%s" ?' % rng_com_port)
    debug_rand = True

# Open the serial port if it isn't open
if not ser.isOpen():
    try:
        ser.open()
    except Exception as e:
        print('Serial port NOT opened! Error: %s' % str(e))
        print('Do you have permissions set to read port: "%s" ?' % rng_com_port)
        print('Continue in DEBUG MODE ON')
        debug_rand = True

# Set Data Terminal Ready to start flow
if not debug_rand:
    ser.setDTR(True)

# This clears the receive buffer so we aren't using buffered data
if not debug_rand:
    ser.flushInput()


# Starting sampling and plotting
bytes_read = bytes(0)
hexadecimal = None
decimal = None
binary = None
data = ""
zeroN = []
oneN = []
mid_line = []
xAxis = []
count = 0  # helps to concatenate the byte string in order to analyse the whole byte string
nRead = 0  # keeps track of the byte read count

# Plot the base graph

plt.ion()
fig = plt.figure(111)
axes = fig.add_subplot(111)  # Add subplot (dont worry only one plot appears)
axes.set_autoscale_on(True)  # enable autoscale
axes.autoscale_view(True, True, True)
axes.set_ylim(0, bit_sample)
l1, = plt.plot(xAxis, zeroN, 'bs', label='Zero count')
l2, = plt.plot(xAxis, oneN, 'r^', label='Ones count')
l3, = plt.plot(xAxis, mid_line, 'g-', label='Mean Distribution ref')
plt.title('Zero/Ones Distribution in time')
plt.ylabel('Zero/Ones Count')
plt.xlabel('Time(s)')
plt.legend(loc='upper right')
plt.show(block=False)

time_start = time.time()
time_actual = time.time() - time_start
time_line = 0
draw_line = True
draw_line1 = True
marker = 0

# loop until int_time (from calibration.ini)
# use a sampling to take N byte per sec: take a byte, wait a fixed delayed time, take another byte and so on...
# in the end reassemble the byte(s) string per sec and analise it
while time_actual < int_time + delay_time:
    time_onSet = time.time() - time_start
    # reset vertical line condition after tot milliseconds
    # it is a trap to capture only one key press at time
    if time_actual-time_line > 0.1 and (not draw_line or not draw_line1):
        time_line = 0
        draw_line = True
        draw_line1 = True
        marker = 0

    # if key press, draw a vertical marker line on plot
    # msvcrt.kbhit() detect keypress in non blocking mode
    # msvcrt.getwch() is useful to omit a double key detection problem
    if msvcrt.kbhit() and draw_line and msvcrt.getwch():
        axes.axvline(x=time_actual)
        marker = time_actual
        draw_line = False
        draw_line1 = False
        time_line = time.time() - time_start

    # Try to read the port
    # noinspection PyBroadException
    try:
        if not debug_rand:
            bytes_read = ser.read(1)  # read one byte at time from serial port
        else:
            bytes_read = os.urandom(int(1))

    except Exception as e:
        print('Read bytes failed! Error: %s' % str(e))
        break

    # Convert bytes to bit
    hexadecimal = binascii.hexlify(bytes_read)
    decimal = int(hexadecimal, 16)
    binary = bin(decimal)[2:].zfill(8)
    # data = "%s" % binary
    data += binary

    time_actual = time.time() - time_start

    # time sleep
    time_delayed = time_actual + delay_time

    # wait for fixed delayed time. Useful to wait a fixed time from a byte catch to another (N bytes sampling per sec)
    while time_actual < time_delayed:
        # if key press, draw a vertical marker line on plot
        if msvcrt.kbhit() and draw_line1 and msvcrt.getwch():
            axes.axvline(x=time_actual)
            draw_line1 = False
            draw_line = False
            marker = time_actual
            time_line = time.time() - time_start
        time.sleep(.01)
        time_actual = time.time() - time_start

    # check if it is the last byte in nRead interval to process
    # it is necessary to assemble the sampling byte in an nRead unique string
    if count == byte_sample - 1:

        # Debugging data read by read
        print('Read %s, onSet time: %s' % (str(nRead), str(time_onSet)))
        # print('Data: %s' % str(data))

        # append results to plot arrays
        zeroN.append(data.count('0'))
        oneN.append(data.count('1'))
        xAxis.append(time_actual)
        mid_line.append(bit_sample / 2)

        # update plot

        l1, = plt.plot(xAxis, zeroN, 'bs', label='Zero count')
        l2, = plt.plot(xAxis, oneN, 'r^', label='Ones count')
        l3, = plt.plot(xAxis, mid_line, 'g-', label='Mean Distribution ref')

        plt.draw()
        # plt.pause(1e-17)
        mypause(0.001)

        # output to file
        dtn = datetime.datetime.now()
        out_file.write(str(debug_rand) + ';')
        out_file.write(str(nRead) + ';')
        out_file.write(str(zeroN[nRead]) + ';')
        out_file.write(str(oneN[nRead]) + ';')
        out_file.write(str(time_onSet) + ';')
        if marker > 0:
            out_file.write(str(marker) + ';')
        else:
            out_file.write(';')
        out_file.write(str(dtn))
        out_file.write('\n')

        # reset condition
        data = ''
        nRead += 1
        count = 0  # reset byte count to start

    else:
        count += 1


print('Read Complete.')
print('Total bytes read: %d' % len(bytes_read))
print('')

# save plot as .png file in project directory
plt.show()
fig1 = plt.gcf()
fig1.savefig(str(csv_len) + '_' + file_plot)

# Close the serial port
ser.close()

out_file.close()

print(' ')

print('FINISHED!')

print(' ')


# Final beep sound
frequency = 1400  # Set Frequency
duration = 1000  # Set Duration in ms
winsound.Beep(frequency, duration)
