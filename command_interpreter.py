#
# Copyright (C) 2023 Texas Instruments Incorporated - http://www.ti.com/
#
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#    Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#    Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
#    Neither the name of Texas Instruments Incorporated nor the names of
#    its contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
'''
Reese Grimsley, October 24, 2023

This script contains code for interpreting command words as recognized from the google Speech Commands dataset by a machine learning model. The sequence of command words is used to define certains action for the camera to take.

The word 'visual' is used as a "command-start", meaning that it must be spoken and followed by a command word that correspond to an action. For example, 'visual' followed by 'right' will result in panning/cropping to the right side of the input image.  
'''

import  time
from enum import Enum

class Actions(Enum):
    '''
    A set of high level actions to take
    '''
    OFF =  0
    PASSTHROUGH = 1
    LEFT = 2
    RIGHT = 3
    UP = 4
    DOWN = 5
    ZOOM = 6

class CommandInterpreter():
    '''
    A class to convert word commands to actions
    '''
    #set of words that correspond to some action
    actionable_commands = ['visual', 'up', 'down', 'forward', 'backward', 'left', 'right', 'off', 'on']
    def __init__(self):
        self.current_action = Actions.PASSTHROUGH
        

    def interpret_commands(self, commands):
        '''
        Interpret a list of command words and produce an action

        :param commands: a list of command words recognized. The first index occurred first in time. This is assumed to be a deque, and will be modified to remove consumed command words
        :return: an Actions enum value
        '''
        print('interpreting commands: ')
        print(commands)
        #signal command has started based on finding 'visual'
        command_started = None
        # We will remove all commands up to this index after finding a command
        command_end_id = -1
        for i, command in enumerate(commands):
            if command.lower() == 'visual':
                command_started = True
            elif command_started is not None: 
                if command in CommandInterpreter.actionable_commands:
                    command_end_id = i
                if command.lower() =='up':
                    self.current_action = Actions.UP
                    print(self.current_action)
                elif command.lower() == 'down': 
                    self.current_action = Actions.DOWN
                    print(self.current_action)                    
                elif command.lower() == 'forward': 
                    self.current_action = Actions.ZOOM
                    print(self.current_action)
                elif command.lower() == 'backward': 
                    self.current_action = Actions.PASSTHROUGH
                    print(self.current_action)
                elif command.lower() == 'off': 
                    self.current_action = Actions.OFF
                    print(self.current_action)
                elif command.lower() == 'on': 
                    self.current_action = Actions.PASSTHROUGH
                    print(self.current_action)
                elif command.lower() == 'left': 
                    self.current_action = Actions.LEFT
                    print(self.current_action)
                elif command.lower() == 'right': 
                    self.current_action = Actions.RIGHT
                    print(self.current_action)
            
        #remove command words that were used
        i = 0
        while i <= command_end_id:
            commands.popleft()
            i+= 1

        return self.current_action