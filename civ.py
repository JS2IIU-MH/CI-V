'''basic example for CI-V programming '''
from datetime import datetime
from logging import getLogger, StreamHandler, FileHandler, Formatter
from logging import DEBUG
import re
import struct
import time

import serial
from serial.tools import list_ports

# Const for I-COM rigs
ICOM_DRIVER_KW = 'CP210x'
DATA_MAX = 11

# CI-V commands
# PREAMBLE, POSAMBLE
PREA = [0xFE, 0xFE]
POSA = [0xFD]

# PC HOST ADDRESS
ADHOST = [0x00]

cmd_read_freq = [0x03]
cmd_read_Smeter = [0x15, 0x02]
cmd_read_spectrum = [0x27, 0x00]
cmd_scope_on = [0x27, 0x10, 0x01]
cmd_scope_off = [0x27, 0x10, 0x00]
cmd_scope_readout_on = [0x27, 0x11, 0x01]
cmd_scope_readout_off = [0x27, 0x11, 0x00]

cmd_pwr_on = [0x18, 0x01]
cmd_pwr_off = [0x18, 0x00]

cmd_temp = []
cmd_vd = [0x15, 0x15]

cmd_read_opmode = [0x04]

cmd_read_gps_pos = [0x23, 0x00]

# Logger setting
logger = getLogger(__name__)
log_fmt = Formatter('%(asctime)s | %(filename)s | %(name)s | %(funcName)s \
                    | %(levelname)s | %(message)s')

shandler = StreamHandler()
shandler.setLevel(DEBUG)
shandler.setFormatter(log_fmt)

fhandler = FileHandler(f'./Log/log_{datetime.now():%Y%m%d%H%M%S}.log', encoding='utf-8')
fhandler.setLevel(DEBUG)
fhandler.setFormatter(log_fmt)

logger.setLevel(DEBUG)
logger.addHandler(shandler)
logger.addHandler(fhandler)
logger.propagate = False


class CIV():
    ''' class CIV, controls i-com rig via CI-V
        direct serial connection or CI-V intercface is necessary
    '''
    def __init__(self, com_port, rig_pn='IC-7300') -> None:
        # rig address and baudrate setting
        logger.info(f'dig part name: {rig_pn}')
        self.addr_rig = self.rig_address(rig_pn)
        rig_baud = self.rig_baudrate(rig_pn)

        # regex pattern for scope data read out
        # self.pat_scope =
        #       re.compile(
        #           r'fefe([0-9]{2})([\w]{2})270000([0-9]{2})([0-9]{2})00([0-9]{10})([0-9]{12})fd'
        #           )
        self.pat_scope = re.compile(
            r'fefe00(\w{2})270000([0-9]{2})([0-9]{2})(\w{24}|\w{50}|\w{100})fd'
            )

        logger.info(f'open com port: {com_port}')
        try:
            self.ser = serial.Serial(port=com_port,
                                     baudrate=rig_baud,
                                     parity=serial.PARITY_NONE,
                                     stopbits=serial.STOPBITS_ONE,
                                     timeout=2)
        except serial.serialutil.SerialException:
            logger.error(f'Serial port exception: {com_port}')

        # self.is_icom_rig = self.check_port()

    def check_port(self):
        ''' check port is for i-com rigs '''
        is_found = False

        ports = list_ports.comports()
        for po in ports:
            res1 = re.findall(ICOM_DRIVER_KW, po.description)
            res2 = re.findall(self.ser.name, po.description)
            if res1 and res2:
                is_found = True

        return is_found

    def send_msg(self, command_list):
        ''' send_msg to rig
            Args:
                command_list, byte-by-byte command in list format
                command_list should include PREA, address and POSA
                ex) [0xFE, 0xFE, 0x94, ...., 0xFD]
            Returns:
                raw buffer bytes content
        '''
        msg = b''
        for cmd in command_list:
            msg = msg + struct.pack('B', cmd)
        self.ser.write(msg)

        self.ser.flush()
        time.sleep(0.2)

        buffer = self.ser.readline()
        return buffer

    def read_msg(self):
        """ read serial communication buffer """
        # TODO: readlineのほうが良いかも
        # buffer = self.ser.read(100)
        buffer = self.ser.readline()
        logger.debug(buffer)
        return buffer

    def pwr_off(self):
        ''' shut down '''
        logger.info('try to shut down connected rig')
        msg_list = PREA + self.addr_rig + ADHOST + cmd_pwr_off + POSA
        self.send_msg(msg_list)

    def pwr_on(self):
        ''' pwr on - does not work on USB connection '''
        logger.info('try to turn on connected rig')
        # baud 19200 -> 0xFE * 25
        NUM_RPT = 25
        WAKE = [0xFE]
        for _ in range(NUM_RPT):
            self.send_msg(WAKE)
        msg_list = PREA + self.addr_rig + ADHOST + cmd_pwr_on + POSA
        self.send_msg(msg_list)

    def read_freq(self):
        ''' Returns Frequency in Hz '''
        logger.info('Reading current Frequency')
        msg_list = PREA + self.addr_rig + ADHOST + cmd_read_freq + POSA
        ret = self.send_msg(msg_list)
        ret_s = ''

        s = re.search(r'fefe00(\w{2})03([0-9]{10})fd', ret.hex())

        if s is not None:
            ret_s = s.group(2)
            # print(len(ret))
        if len(ret_s) == 10:
            # 送信したメッセージから0xfdの2文字分減らして帰ってきた文字のみ抽出する=周波数の文字列
            # ret = ret[(len(msg_list) - 1) * 2:-2]
            freq = self.reverse_msg(ret_s)
            freq = int(freq)
            logger.debug(f'Freq raw msg: {freq}')
        else:
            logger.error('Frequency read out was failed')
            freq = 0

        return freq

    def stop_scope_readout(self):
        """ scope readout stop """
        msg_list = PREA + self.addr_rig + ADHOST + cmd_scope_readout_off + POSA
        self.send_msg(msg_list)

    def start_scope_readout(self):
        """ scope readout start """
        msg_list = PREA + self.addr_rig + ADHOST + cmd_scope_readout_on + POSA
        self.send_msg(msg_list)

    def read_spectrum(self, is_1st=False):
        ''' read out spectrum scope data from IC-7300
            Args:
                is_1st: if 1st time run, set True
            Returns:
                scope_data_list: data as int
                center_freq: scope center frequency in Hz
                span: frequency span in Hz
        '''
        count = 0
        ret_dat = bytes(0)

        # if sspectrum scope is not shown in rig's display, turn on scope
        if is_1st:
            # scope on
            msg_list = PREA + self.addr_rig + ADHOST + cmd_scope_on + POSA
            self.send_msg(msg_list)
            # scope readout on
            msg_list = PREA + self.addr_rig + ADHOST + cmd_scope_readout_on + POSA
            self.send_msg(msg_list)

            # read spectrum data
            msg_list = PREA + self.addr_rig + ADHOST + cmd_read_spectrum + POSA
            ret_dat = self.send_msg(msg_list)
            logger.debug(f'ret_dat: {ret_dat}')
        # print(ret.hex())
        while count < 15:
            ret_dat = ret_dat + self.ser.readline()
            count += 1

        # find read out response
        # ACK: fefe0094 27 00 00 fa fd
        # data1: fefe0094 27 00 00 01 11 00 ********** 00 ********** fd
        # data2-11: fefe0094 27 00 ## 11 **data(50/100)** fd
        #
        # regex pattern definition in self.__init__()
        # pat_scope =
        #       re.compile(
        #           r'fefe([0-9]{2})([0-9]{2})270000([0-9]{2})([0-9]{2})00([0-9]{10})([0-9]{12})fd'
        #           )
        # [('00', '94', '01', '11', '000030660900002500000000')]
        # self.pat_scope =
        #       re.compile(r'fefe00(\w{2})270000([0-9]{2})([0-9]{2})(\w{24}|\w{50}|\w{100})fd')
        res = re.findall(self.pat_scope, ret_dat.hex())
        logger.debug(f'res: {res}')

        count = 1
        scope_data = ''
        scope_data_list = []
        center_freq = 0
        span = 0

        is_find_1st = False
        is_complete = False

        for d in res:
            # print(d[0])
            if not is_complete:
                if not is_find_1st:
                    if d[1] == '01':
                        # d[1] == NOW
                        # ### check freq/span
                        data = d[3]
                        # d[3] = centerfreq + span
                        center_freq = self.decode_freq(data[2:12])
                        # print(center_freq, data[2:12])
                        span = self.decode_span(data[12:])
                        # print(f'centfreq: {center_freq:,} Hz, span: {span:,} Hz')
                        logger.debug(f'Centfreq: {center_freq:,} Hz, Span: {span:,} Hz')
                        is_find_1st = True
                else:
                    # ### add data
                    scope_data = scope_data + d[3]
                    if d[1] == '11':
                        is_find_1st = False
                        data_list = self.scope_data_to_list(scope_data)
                        for da in data_list:
                            scope_data_list.append(int(da, 16))
                        is_complete = True

        logger.debug(f'scope data: {scope_data_list}')

        return scope_data_list, center_freq, span

    @classmethod
    def scope_data_to_list(cls, scope_data):
        """ scopedata format change from continuous string to splitted string list """
        SCOPE_DATA_LENGTH = 475 * 2
        out_data = []
        if len(scope_data) == SCOPE_DATA_LENGTH:
            for i in range(SCOPE_DATA_LENGTH // 2):
                out_data.append(scope_data[i*2:i*2+2])

        return out_data

    @classmethod
    def decode_freq(cls, freq_string):
        """ decode frequency format """
        FREQ_FULL_LENGTH = 10
        FREQ_LENGTH = 10
        if len(freq_string) == FREQ_FULL_LENGTH:
            freq = ''
            tmp = []
            # 最初の2文字を捨てる
            # freq_string = freq_string[2:]
            for i in range(FREQ_LENGTH // 2):
                tmp.append(freq_string[2*i:2*i+2])
            for i in range(FREQ_LENGTH // 2):
                freq = freq + tmp[FREQ_LENGTH // 2 - i - 1]
        else:
            freq = 0

        return int(freq)

    @classmethod
    def decode_span(cls, span_string):
        ''' decode span string, returns span in Hz'''
        SPAN_FULL_LENGTH = 12
        if len(span_string) == SPAN_FULL_LENGTH:
            span = int(span_string[2:3]) * 1000\
                 + int(span_string[3:4]) * 100\
                 + int(span_string[4:5]) * 100000\
                 + int(span_string[5:6]) * 10000
        else:
            span = 0
        return span

    @classmethod
    def serial_port_list(cls):
        """ returns serial port list """
        port_list = []
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            # if 'USB Serial Port' in p.description:
            port_list.append(p.device)

        return port_list

    def read_spectrum_to_file(self):
        """ spectrum data save to csv """
        logger.info('output spectrum data to csv')
        # READ_MAX = 11
        filename = f'./Log/spectrum_{datetime.now()::%Y%m%d_%H%M%S}.csv'
        logger.info(f'filename: {filename}')
        count = 0

        # scope on
        msg_list = PREA + self.addr_rig + ADHOST + cmd_scope_on + POSA
        self.send_msg(msg_list)

        # scope readout on
        msg_list = PREA + self.addr_rig + ADHOST + cmd_scope_readout_on + POSA
        self.send_msg(msg_list)

        with open(filename, 'w', encoding='utf-8') as f:
            # data request
            msg_list = PREA + self.addr_rig + ADHOST + cmd_read_spectrum + POSA
            ret = self.send_msg(msg_list)
            f.write(ret.hex() + '\n')

            while count < 10:
                ret = self.ser.readline()
                f.write(ret.hex())
                # print(f'#{count:02} {ret.hex()}')
                count += 1

    def read_temp(self):
        """ request temperature information """
        msg_list = PREA + self.addr_rig + ADHOST + cmd_temp + POSA
        ret = self.send_msg(msg_list)
        return ret

    def read_vd(self):
        """ read Vd value in V, IC-7300 only"""
        msg_list = PREA + self.addr_rig + ADHOST + cmd_vd + POSA
        ret = self.send_msg(msg_list)
        s = re.search(r'fefe00([\w]{2})1515([0-9]{4})fd', ret.hex())
        if s is not None:
            val = int(s.group(1))
            # print(val)
        else:
            val = -1

        if val < 0 or val > 255:
            out_val = 0.0
        elif val < 14:
            out_val = 10 / 13 * val
        else:
            out_val = 6 / 228 * val + 10

        return out_val

    def read_opmode(self):
        ''' returnd mode in string'''
        opmode_str = ['LSB', 'USB', 'AM', 'CW', 'RTTY',
                      'FM', 'Reserved', 'CW-R', 'RTTY-R', 'N/A',
                      'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
                      'N/A', 'N/A', 'DV']

        msg_list = PREA + self.addr_rig + ADHOST + cmd_read_opmode + POSA
        ret = self.send_msg(msg_list)
        s = re.search(r'fefe00([\w]{2})04([0-9]{4})fd', ret.hex())

        if s is not None:
            # print(s.group(2))
            num = int(s.group(2)[:2])
        else:
            num = 9

        return opmode_str[num]

    def read_gps_position(self):
        """ read out GPS position data
            Returns:
                tuple latitude, longitude
        """
        # cmd_read_gps_pos
        msg_list = PREA + self.addr_rig + ADHOST + cmd_read_gps_pos + POSA
        ret = self.send_msg(msg_list)
        pat_gps = re.compile(
            r'fefe00(\w{2})2300([0-9]{10})([0-9]{12})(\w{8})([0-9]{4})([0-9]{6})([0-9]{14})fd'
            )
        s = re.findall(pat_gps, ret.hex())
        # print(s)
        lat = s[0][1]
        lon = s[0][2]
        alt = s[0][3]
        time_utc = s[0][6]
        # print(f'latitude: {lat}, longitude: {lon}, altitude: {alt}, time: {time_utc}')
        logger.debug(f'latitude: {lat}, longitude: {lon}, altitude: {alt}, time: {time_utc}')

        return lat, lon

    @classmethod
    def reverse_msg(cls, msg_in):
        """ reverse msg from rig, ex frequency etc. """
        # 2桁ずつ、逆順に並んでいるので入れ替える
        num = len(msg_in)
        out_msg = ''
        if num % 2 == 0:
            for i in range(int(num / 2)):
                out_msg = out_msg + msg_in[num-i*2-2:num-i*2]
            return out_msg
        else:
            return ''

    @classmethod
    def rig_address(cls, rig_pn):
        """ returns rig's CI-V address in [string] """
        rig_address_dict = {
            'IC-7300': 0x94,
            'ID-51': 0x86,
            'IC-R6': 0x7E,
        }
        try:
            rig_address = rig_address_dict[rig_pn]
        except KeyError:
            # print(f'KeyError: {rig_pn} is not in list')
            logger.error(f'KeyError: {rig_pn} is not in list')
            rig_address = 0x00

        return [rig_address]

    @classmethod
    def rig_baudrate(cls, rig_pn):
        """ returns rig's max baudrate [bps] in int """
        rig_baud_dict = {
            'IC-7300': 115200,
            'ID-51': 19200,
            'IC-R6': 19200,
        }
        try:
            rig_baud = rig_baud_dict[rig_pn]
        except KeyError:
            # print(f'KeyError: {rig_pn} is not in list')
            logger.error(f'KeyError: {rig_pn} is not in list')
            rig_baud = 19200

        return rig_baud

    def __del__(self):
        try:
            self.ser.close()
        except AttributeError:
            pass


def main():
    ''' main func for test purpose '''
    # civ = CIV('COM5', 'IC-R6')
    civ = CIV('COM5', 'ID-51')

    # リグに表示されている周波数[Hz] を取得する。
    print(f'Frequency: {civ.read_freq():,} Hz')
    # civ.pwr_off()
    # l, cf, sp = civ.read_spectrum(True)
    # print(cf, sp)
    # print(l)

    # civ.read_vd()
    # civ.read_freq()
    print(civ.read_opmode())
    print(civ.read_gps_position())
    # print(civ.serial_port_list())


if __name__ == '__main__':
    main()
