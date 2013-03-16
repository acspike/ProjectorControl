#
# projectorcontrol.py
# Copyright (c) 2007-2013 Aaron C Spike
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 


from Tkinter import *
import serial
import ConfigParser
import os
import sets

PADDING=5

class MyConfigParser(ConfigParser.RawConfigParser):
    def __init__(self, config_file=None):
        ConfigParser.RawConfigParser.__init__(self)
        if config_file:
            self.read(config_file)
    def optionxform(self, option):
        '''overrides parent method of same name to prevent lowercasing options'''
        return option
    def get_default(self, section, option, val):
        if not self.has_option(section, option):
            return val
        else:
            return self.get(section, option)
    def getboolean_default(self, section, option, val):
        if not self.has_option(section, option):
            return bool(val)
        else:
            return self.getboolean(section, option)

class ValueScanner(object):
    def __init__(self, pc, label, set_cmd, get_cmd, value_list):
        self.pc = pc
        self.set_cmd = set_cmd
        self.get_cmd = get_cmd
        self.value_list = sorted(list(sets.Set(value_list)))
        frame = LabelFrame(pc, text=label)
        Button(frame, text='Get', command=self.get).pack(side=LEFT,fill=BOTH,expand=True)
        Button(frame, text='Set', command=self.set).pack(side=LEFT,fill=BOTH,expand=True)
        Button(frame, text='Scan', command=self.scan).pack(side=LEFT,fill=BOTH,expand=True)
        self.entry = Entry(frame)
        self.entry.pack(side=LEFT,fill=BOTH,expand=True)
        frame.pack(fill=BOTH,expand=True)
    def get(self):
        val = self.pc.send_command(self.get_cmd)
        self.entry.delete(0,END)
        if val and isinstance(val, str):
            self.entry.insert(END,val)
        return val
    def set(self, val=None):
        do_update = False
        if not val:
            do_update = True
            val = self.entry.get()
        retval = self.pc.send_command('%s %s' % (self.set_cmd,val))
        if do_update:
            retval = self.get()
        return retval
    def scan(self):
        retval = None
        start = -1
        try:
            start = self.value_list.index(self.get())+1
        except ValueError:
            pass
        for i in self.value_list[start:] + self.value_list:
            result = self.set(i)
            if result:
                retval = self.get()
                break
        return retval

class ProjectorControllFrame(LabelFrame):
    def __init__(self, parent, config=None, section_prefix='', **kwargs):
        label = config.get_default(section_prefix+'general','label','')
        LabelFrame.__init__(self, parent, text=label, padx=PADDING, pady=PADDING, **kwargs)
        port_name = config.get_default(section_prefix+'general','port','COM1')
        self.port = serial.Serial(port=port_name,timeout=3)
        
        self.make_on_off_frame('Power','pwr')
        if config.getboolean_default(section_prefix+'general','mute',False):
            self.make_on_off_frame('Mute','mute')
        self.make_control_frame('Muting Option','msel',config,section_prefix+'mutes')
        self.make_control_frame('Video Source','source',config,section_prefix+'sources')
        if config.getboolean_default(section_prefix+'general','source',False):
            value_list = ['B0','B1','B2','B3','B4'] + ['%02d' % x for x in range(50)]
            ValueScanner(self, 'Video Source', 'source','source?',value_list)
        self.make_control_frame('Aspect Ratio','aspect',config,section_prefix+'aspects')
        if config.getboolean_default(section_prefix+'general','mount',False):
            self.make_on_off_frame('Vertical Mount','vreverse','Ceiling','Floor')
            self.make_on_off_frame('Horizontal Mount','hreverse','Rear','Front')
    
    def read(self):
        retval = None
        
        raw_value = self.port.read()
        while raw_value[-1] != ':':
            raw_value += self.port.read()

        if raw_value == 'ERR\r:':
            retval == False
        elif raw_value.find('=') != -1:
            retval = raw_value.rstrip('\r:').split('=')[1]
        elif raw_value == ':':
            retval = True
        return retval
    
    def send_command(self, cmd):
        self.port.write(cmd.upper() + '\n\r')
        return self.read()
    
    def make_command(self, cmd):
        def func():
            self.send_command(cmd)
        return func
    
    def make_on_off_frame(self, label, cmd, on='On', off='Off'):
        frame = LabelFrame(self, text=label, padx=PADDING, pady=PADDING)
        Button(frame, text=on, command=self.make_command('%s on' % (cmd))).pack(side=LEFT,fill=BOTH,expand=True)
        Button(frame, text=off, command=self.make_command('%s off' % (cmd))).pack(side=LEFT,fill=BOTH,expand=True)
        frame.pack(fill=BOTH,expand=True)
        
    def make_control_frame(self, label, cmd, config, section):
        if config.has_section(section):
            frame = LabelFrame(self, text=label, padx=PADDING, pady=PADDING)
            for name, value in config.items(section):
                Button(frame, text=name, command=self.make_command('%s %s' % (cmd,value))).pack(fill=BOTH,expand=True)
            frame.pack(fill=BOTH,expand=True)

class ProjectorController(object):
    def __init__(self, config_file):
        config = MyConfigParser(config_file)
        self.master = Tk()
        self.master.title('Projector Control')
        tempdir = os.environ.get('_MEIPASS2',None)
        icon = 'Projector.ico'
        if tempdir:
            icon = os.path.join(tempdir,icon)
        self.master.iconbitmap(icon)
        
        prefixes = [x[:-len('general')] for x in config.sections() if x.endswith('general')]
        for p in prefixes:
            pc = ProjectorControllFrame(self.master, config=config, section_prefix=p)
            pc.pack(side=LEFT,fill=BOTH,expand=True, padx=PADDING, pady=PADDING)

app = ProjectorController('config.ini')
mainloop()
