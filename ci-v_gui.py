''' CI-V interface monitor '''

import tkinter as tk
from tkinter import ttk
import threading
import time
import numpy as np

import matplotlib.pyplot as plt
# from matplotlib import animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import civ


class Application(tk.Frame):
    ''' GUI Application '''
    def __init__(self, master) -> None:
        super().__init__(master)
        self.grid()

        self.is_connected = False

        self.scope_data_list = []
        self.center_freq = 0
        self.span = 0

        self.flg_scope_run = False
        self.rig_info_update_count = 0

        BUTTON_WIDTH_MID = 12
        LABEL_WIDTH_MID = 12

        frame1 = tk.Frame(master)
        self.label_freq = tk.Label(frame1, text='--- Hz', width=20, font=('Calibri', 26, 'bold'))
        self.label_freq.grid(row=0, column=0)
        self.label_mode = tk.Label(frame1, text='MODE', width=10, font=('Calibri', 16, 'bold'))
        self.label_mode.grid(row=0, column=1)
        frame1.grid(pady=5)

        frame2 = tk.Frame(master)
        self.gen_graph(frame2)
        frame2.grid(pady=5)

        frame3 = tk.Frame(master)
        self.button_scope_run = tk.Button(frame3, text='Scope Run',
                                          width=BUTTON_WIDTH_MID,
                                          font=('Calibri', 14, 'bold'),
                                          command=self.com_scope_run)
        self.button_scope_run.grid(row=0, column=0)
        self.button_scope_stop = tk.Button(frame3, text='Scope Stop',
                                           width=BUTTON_WIDTH_MID,
                                           font=('Calibri', 14, 'bold'),
                                           command=self.com_scope_stop)
        self.button_scope_stop.grid(row=0, column=1)
        self.button_save = tk.Button(frame3, text='Save', width=BUTTON_WIDTH_MID,
                                     font=('Calibri', 14, 'bold'))
        self.button_save.grid(row=0, column=2)
        frame3.grid(pady=5)

        frame4 = tk.Frame(master)
        self.label_vd = tk.Label(frame4, text='Vd', width=LABEL_WIDTH_MID,
                                 font=('Calibri', 14, 'bold'))
        self.label_temp = tk.Label(frame4, text='Temp', width=LABEL_WIDTH_MID,
                                   font=('Calibri', 14, 'bold'))
        button_rig_on = tk.Button(frame4, text='Rig On', width=BUTTON_WIDTH_MID,
                                  font=('Calibri', 14, 'bold'),
                                  command=self.com_rig_on)
        button_rig_off = tk.Button(frame4, text='Rig Off', width=BUTTON_WIDTH_MID,
                                   font=('Calibri', 14, 'bold'),
                                   command=self.com_rig_off)
        button_connect = tk.Button(frame4, text='Connect', width=BUTTON_WIDTH_MID,
                                   font=('Calibri', 14, 'bold'),
                                   command=self.com_connect)
        combobox_com = ttk.Combobox(frame4, values=civ.CIV.serial_port_list(), height=3)
        combobox_com.set('select com port')

        self.label_vd.grid(row=0, column=0)
        combobox_com.grid(row=0, column=1)
        button_connect.grid(row=0, column=2)
        self.label_temp.grid(row=1, column=0)
        button_rig_on.grid(row=1, column=1)
        button_rig_off.grid(row=1, column=2)
        frame4.grid(pady=5)

        frame5 = tk.Frame(master)
        button_exit = tk.Button(frame5, text='Exit', command=quit,
                                width=BUTTON_WIDTH_MID, font=('Calibri', 14, 'bold'))
        button_exit.grid()
        frame5.grid(pady=5)

        ##
        # ci-v instance
        self.my_rig = civ.CIV('COM5')
        # is_connected = True
        time.sleep(1)
        self.my_rig.stop_scope_readout()
        self.rig_data_update()
        time.sleep(1)

        # threading
        self.thread1 = threading.Thread(target=self.th_info_update, daemon=True)
        self.thread1.start()

        self.thread2 = threading.Thread(target=self.th_data_update, daemon=True)
        self.thread2.start()

        # frame1a = tk.Frame()
        # self.gen_mpl_graph(frame1a)
        # frame1a.grid()

    def com_scope_run(self):
        if self.flg_scope_run is False:
            self.flg_scope_run = True

    def com_scope_stop(self):
        if self.flg_scope_run is True:
            self.flg_scope_run = False

    def com_save(self):
        pass

    def com_connect(self):
        self.rig_data_update()

    def com_rig_on(self):
        self.my_rig.pwr_on()

    def com_rig_off(self):
        ''' shut down rig'''
        self.my_rig.pwr_off()

    def gen_graph(self, master):
        ''' draw pectrum scope '''
        self.fig, self.ax = plt.subplots()
        self.fig.set_figwidth(5)
        self.fig.set_figheight(2)

        # dummy data for initial plot
        dummy_x = np.linspace(0, 200, 475)
        dummy_y = np.linspace(10, 150, 475)

        (self.graph,) = self.ax.plot(dummy_x, dummy_y, linewidth=1)
        # self.ax.set_xlabel('Freqency')
        # ax.set_ylabel('Amplitude')
        # ax.set_title('Spectrum Scope')
        self.ax.grid()

        # MatplotlibのFigureをTkinterのCanvasに埋め込む
        canvas = FigureCanvasTkAgg(self.fig, master=master)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def redraw_graph(self, event=None):
        # dummy
        # dummy_x = np.linspace(0, 200, 475)
        # dummy_y = np.linspace(30, 120, 475)

        SCOPE_DATA_LENGTH = 475

        if len(self.scope_data_list) == SCOPE_DATA_LENGTH:
            x = np.linspace(self.center_freq - self.span, self.center_freq + self.span,
                            SCOPE_DATA_LENGTH)
            y = self.scope_data_list

            self.graph.set_xdata(x)
            self.graph.set_ydata(y)

            self.ax.set_xlim(self.center_freq - self.span, self.center_freq + self.span)
            self.ax.set_xticks(self.span_to_xticks(self.center_freq, self.span))
            self.ax.set_xticklabels(self.span_to_xticklabels(self.span), fontsize=6)

            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
            time.sleep(0.1)

    def rig_data_update(self):
        # print('hh')
        # freq
        freq = self.my_rig.read_freq()
        if freq != 0:
            self.label_freq['text'] = f'{freq:,} Hz'

        # mode
        if self.my_rig.read_opmode() != 'N/A':
            self.label_mode['text'] = self.my_rig.read_opmode()

        # Vd
        vd = self.my_rig.read_vd()
        # print(vd)
        if vd != 0:
            self.label_vd['text'] = f'Vd: {vd:.3g} V'

    def span_to_xticklabels(self, span):
        NUM_XTICKS_LABEL = 11
        span = span / 1000
        xticks_list = np.linspace(start=-span, stop=span, num=NUM_XTICKS_LABEL)

        return xticks_list

    def span_to_xticks(self, center_freq, span):
        NUM_XTICKS_LABEL = 11
        tick_start = center_freq - span
        tick_stop = center_freq + span

        xticks_list = np.linspace(start=tick_start, stop=tick_stop,
                                  num=NUM_XTICKS_LABEL)

        return xticks_list

    def th_info_update(self):
        while True:
            self.rig_data_update()
            time.sleep(3)

    def th_data_update(self):
        RIG_INFO_INTERVAL = 3000

        # start scope readout
        self.my_rig.start_scope_readout()

        while True:
            # print(self.rig_info_update_count)
            if self.flg_scope_run:
                self.scope_data_list, self.center_freq, self.span\
                    = self.my_rig.read_spectrum(True)

                # update graph
                self.redraw_graph()
                # time.sleep(0.5)

                # freq update
                if self.center_freq != 0:
                    self.label_freq['text'] = f'{self.center_freq:,} Hz'

            if self.rig_info_update_count == RIG_INFO_INTERVAL:
                # stop scope readout
                self.my_rig.stop_scope_readout()
                # rig info update
                self.rig_data_update()
                # start scope readout
                self.my_rig.start_scope_readout()
                self.rig_info_update_count = 0
            else:
                self.rig_info_update_count += 1

    def __del__(self):
        ''' destructor '''
        self.my_rig.stop_scope_readout()
        # self.thread1.join()
        self.thread2.join()


def main():
    ''' main function generating window instance '''
    root = tk.Tk()
    root.title("CI-V Rig Monitor by JS2IIU")
    root.geometry('550x500')
    root.grid_anchor(tk.CENTER)

    app = Application(master=root)

    app.mainloop()


if __name__ == '__main__':
    main()
