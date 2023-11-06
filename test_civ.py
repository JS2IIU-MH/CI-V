'''basic example for CI-V programming '''
import re
import struct

import serial
from serial.tools import list_ports

## Const for I-COM rigs
ICOM_DRIVER_KW = 'CP210x'

## CI-V commands
PREAMBLE = [0xFE, 0xFE]
POSTAMBLE = [0xFD]

ADDR_RIG = [0x94]
ADDR_HOST = [0x00]

cmd_read_freq = [0x03]
cmd_read_Smeter = [0x15, 0x02]


class CIV():
    ''' class CIV, controls i-com rig via CI-V
        direct serial connection or CI-V intercface is necessary
    '''
    def __init__(self, com_port) -> None:
        self.ser = serial.Serial(port=com_port,
                                 baudrate=19200,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE,
                                 timeout=1)
        self.is_icom_rig = self.check_port()

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

        buffer = self.ser.readline()
        return buffer

    def read_freq(self):
        ''' Returns Frequency in Hz '''
        msg_list = PREAMBLE + ADDR_RIG + ADDR_HOST + cmd_read_freq + POSTAMBLE
        ret = self.send_msg(msg_list)
        # ret.hex() で文字列に。
        ret = ret.hex()

        # 送信したメッセージから0xfdの2文字分減らして帰ってきた文字のみ抽出する=周波数の文字列
        ret = ret[(len(msg_list) - 1) * 2:-2]
        # 2桁ずつ、逆順に並んでいるので入れ替える
        freq = ''
        # print(len(ret))
        for i in range(int(len(ret)/2)):
            # print(ret[(4-i)*2:(4-i)*2 + 2])
            freq = freq + ret[(4-i)*2:(4-i)*2 + 2]

        return int(freq)

    def __del__(self):
        self.ser.close()

def main():
    ''' main func for test purpose '''
    civ = CIV('COM3')

    # リグに表示されている周波数[Hz] を取得する。
    print(f'Frequency: {civ.read_freq():,} Hz')

if __name__ == '__main__':
    main()
