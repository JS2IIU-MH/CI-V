'''basic example for CI-V programming '''
import re
import struct
import time

import serial
from serial.tools import list_ports

# Const for I-COM rigs
ICOM_DRIVER_KW = 'CP210x'
DATA_MAX = 11

# CI-V commands
PREAMBLE = [0xFE, 0xFE]
POSTAMBLE = [0xFD]

# ID-51
# ADDR_RIG = [0x86]

# IC-R6
ADDR_RIG = [0x7E]

# IC-7300
# ADDR_RIG = [0x94]

# PC HOST ADDRESS
ADDR_HOST = [0x00]

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


class CIV():
    ''' class CIV, controls i-com rig via CI-V
        direct serial connection or CI-V intercface is necessary
    '''
    def __init__(self, com_port, rig_pn='IC-7300') -> None:
        # regex pattern for scope data read out
        self.addr_rig = self.rig_address(rig_pn)

        # only for IC-7300
        # if ADDR_RIG == [0x94]:
        #     self.pat_01 = re.compile(r'fefe0094270000([0-9]{2})([0-9]{2})([0-9]+)fd')
        #     self.pat_02 = re.compile(r'fefe0094270000([0-9]{2})([0-9]{2})(\w{50,100})fd')
        #     # pat_11 = re.compile(r'fefe0094270000([0-9]{2})([0-9]{2})(\w{50})fd')
        #     self.pat_all = re.compile(r'fefe0094270000([0-9]{2})([0-9]{2})(\w{24}|\w{50}|\w{100})fd')

        self.pat_scope = re.compile(r'fefe([0-9]{2})([\w]{2})270000([0-9]{2})([0-9]{2})00([0-9]{10})([0-9]{12})fd')

        self.ser = serial.Serial(port=com_port,
                                 baudrate=115200,
                                 # baudrate=19200,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE,
                                 timeout=2)
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
                command_list should include preamble, address and postamble
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
        print(buffer)
        return buffer

    def pwr_off(self):
        ''' shut down '''
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_pwr_off + POSTAMBLE
        _ = self.send_msg(msg_list)

    def pwr_on(self):
        ''' pwr on - does not work on USB connection '''
        # baud 19200 -> 0xFE * 25
        NUM_RPT = 25
        WAKE = [0xFE]
        for _ in range(NUM_RPT):
            _ret = self.send_msg(WAKE)
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_pwr_on + POSTAMBLE
        _ = self.send_msg(msg_list)

    def read_freq(self):
        ''' Returns Frequency in Hz '''
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_read_freq + POSTAMBLE
        ret = self.send_msg(msg_list)
        ret_s = ''

        # pat = re.compile(r'fefe([0-9]{2})([0-9]{2})270000([0-9]{2})([0-9]{2})00([0-9]{10})([0-9]{12})fd')
        # if ADDR_RIG == [0x94]:
        #     s = re.search(r'fefe009403([0-9]{10})fd', ret.hex())
        # elif ADDR_RIG == [0x86]:
        #     s = re.search(r'fefe008603([0-9]{10})fd', ret.hex())
        # elif ADDR_RIG == [0x7E]:
        #     s = re.search(r'fefe007e03([0-9]{10})fd', ret.hex())
        s = re.search(r'fefe00([\w]{2})03([0-9]{10})fd', ret.hex())

        if s is not None:
            ret_s = s.group(2)
            # print(len(ret))
        if len(ret_s) == 10:
            # 送信したメッセージから0xfdの2文字分減らして帰ってきた文字のみ抽出する=周波数の文字列
            # ret = ret[(len(msg_list) - 1) * 2:-2]
            freq = self.reverse_msg(ret_s)
            freq = int(freq)
            # print(freq)
        else:
            freq = 0

        return freq

    def stop_scope_readout(self):
        """ scope readout stop """
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_scope_readout_off + POSTAMBLE
        _ = self.send_msg(msg_list)

    def start_scope_readout(self):
        """ scope readout start """
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_scope_readout_on + POSTAMBLE
        _ = self.send_msg(msg_list)

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
            msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_scope_on + POSTAMBLE
            _ = self.send_msg(msg_list)
            # scope readout on
            msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_scope_readout_on + POSTAMBLE
            _ = self.send_msg(msg_list)

            # read spectrum data
            msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_read_spectrum + POSTAMBLE
            ret_dat = self.send_msg(msg_list)
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
        # res = re.findall(self.pat_all, ret_dat.hex())
        # res_data = re.findall(self.pat_02, ret_dat.hex())
        #
        # pat_scope = re.compile(r'fefe([0-9]{2})([0-9]{2})270000([0-9]{2})([0-9]{2})00([0-9]{10})([0-9]{12})fd')
        # [('00', '94', '01', '11', '000030660900002500000000')]
        res = re.findall(self.pat_scope, ret_dat.hex())

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
                    if d[2] == '01':
                        # d[2] == NOW
                        # ### check freq/span
                        data = d[4]
                        # d[4] = centerfreq + span
                        center_freq = self.decode_freq(data[2:12])
                        # print(center_freq, data[2:12])
                        span = self.decode_span(data[12:])
                        # print(f'centfreq: {center_freq:,} Hz, span: {span:,} Hz')
                        is_find_1st = True
                else:
                    # ### add data
                    scope_data = scope_data + d[4]
                    if d[2] == '11':
                        is_find_1st = False
                        data_list = self.scope_data_to_list(scope_data)
                        for da in data_list:
                            scope_data_list.append(int(da, 16))
                        is_complete = True

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
        # READ_MAX = 11
        filename = 'spectrum_out2.txt'
        count = 0

        # scope on
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_scope_on + POSTAMBLE
        _ = self.send_msg(msg_list)

        # scope readout on
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_scope_readout_on + POSTAMBLE
        _ = self.send_msg(msg_list)

        with open(filename, 'w', encoding='utf-8') as f:
            # data request
            msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_read_spectrum + POSTAMBLE
            ret = self.send_msg(msg_list)
            f.write(ret.hex() + '\n')

            while count < 10:
                ret = self.ser.readline()
                f.write(ret.hex())
                # print(f'#{count:02} {ret.hex()}')
                count += 1

    def read_temp(self):
        """ request temperature information """
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_temp + POSTAMBLE
        ret = self.send_msg(msg_list)
        return ret

    def read_vd(self):
        """ read Vd value in V, IC-7300 only"""
        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_vd + POSTAMBLE
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
                      'FM', 'Reserved', 'CW-R', 'RTTY-R', 'N/A']

        msg_list = PREAMBLE + self.addr_rig + ADDR_HOST + cmd_read_opmode + POSTAMBLE
        ret = self.send_msg(msg_list)
        s = re.search(r'fefe00([\w]{2})04([0-9]{4})fd', ret.hex())

        if s is not None:
            print(s.group(2))
            num = int(s.group(2)[:2])
        else:
            num = 9

        # print(f'RO{opmode_str[num]}: {num}, {ret.hex()}')

        return opmode_str[num]

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
        return ''
    
    @classmethod
    def rig_address(cls, rig_pn):
        """ returns rig's CI-V address in string """
        RIG_ADDRESS_DICT = {
            'IC-7300': '0x94',
            'ID-51': '0x86',
            'IC-R6': '0x7E',
        }
        try:
            rig_address = RIG_ADDRESS_DICT[rig_pn]
        except KeyError:
            print(f'KeyError: {rig_pn} is not in list')
            rig_address = '0x00'
        
        return rig_address

    def __del__(self):
        try:
            self.ser.close()
        except AttributeError:
            pass


def main():
    ''' main func for test purpose '''
    civ = CIV('COM5', 'IC-7300')

    # リグに表示されている周波数[Hz] を取得する。
    print(f'Frequency: {civ.read_freq():,} Hz')
    # civ.pwr_off()
    # l, cf, sp = civ.read_spectrum(True)
    # print(cf, sp)
    # print(l)

    # civ.read_vd()
    # civ.read_freq()
    # print(civ.read_opmode())
    # print(civ.serial_port_list())


if __name__ == '__main__':
    main()
