# ------------------------------------------------------------------------------------------------
# Copyright (c) 2016 Microsoft Corporation
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ------------------------------------------------------------------------------------------------

# Human Action Component - use this to let humans play through the same missions as you give to agents

import MalmoPython
import os
import sys
import time
from Tkinter import *
import tkMessageBox
from PIL import Image
from PIL import ImageTk

class HumanAgentHost:

    def __init__( self, args, my_mission, my_mission_record, action_space ):
        '''Initializes the class and runs a mission.
        
        Parameters:
        args : list of strings, containing the command-line arguments (pass an empty list if unused).
        mission_spec : MissionSpec instance, specifying the mission.
        mission_record_spec : MissionRecordSpec instance, specifying what should be recorded.
        action_space : string, either 'continuous' or 'discrete' that says which commands to generate.
        '''
        self.createGUI()

        self.agent_host = MalmoPython.AgentHost()
        try:
            self.agent_host.parse( args )
        except RuntimeError as e:
            print 'ERROR:',e
            print self.agent_host.getUsage()
            exit(1)
        if self.agent_host.receivedArgument("help"):
            print self.agent_host.getUsage()
            exit(0)
            
        self.runMission( my_mission, my_mission_record, action_space )
            
    def createGUI( self ):
        '''Create the graphical user interface.'''
        our_font = "Helvetica 16 bold"
        small_font = "Helvetica 9 bold"
        self.root = Tk()
        self.root.wm_title("Human Action Component")
        self.canvas = Canvas(self.root, borderwidth=0, highlightthickness=0, bg="white" )
        self.canvas.bind('<Motion>',self.onMouseMoveInCanvas)
        self.canvas.bind('<Button-1>',self.onLeftMouseDownInCanvas)
        self.canvas.bind('<ButtonRelease-1>',self.onLeftMouseUpInCanvas)
        if sys.platform == 'darwin': right_mouse_button = '2' # on MacOSX, the right button is 'Button-2'
        else:                        right_mouse_button = '3' # on Windows and Linux the right button is 'Button-3'
        self.canvas.bind('<Button-'+right_mouse_button+'>',self.onRightMouseDownInCanvas)
        self.canvas.bind('<ButtonRelease-'+right_mouse_button+'>',self.onRightMouseUpInCanvas)
        self.canvas.bind('<KeyPress>',self.onKeyPressInCanvas)
        self.canvas.bind('<KeyRelease>',self.onKeyReleaseInCanvas)
        self.canvas.pack(padx=5, pady=5)
        self.entry_frame = Frame(self.root)
        Label(self.entry_frame, text="Command:",font = our_font).pack(padx=5, pady=5, side=LEFT)
        self.command_entry = Entry(self.entry_frame,font = our_font)
        self.command_entry.bind('<Key>',self.onKeyInCommandEntry)
        self.command_entry.pack(padx=5, pady=5, side=LEFT)
        Button(self.entry_frame, text='Send', command=self.onSendCommand,font = our_font).pack(padx=5, pady=5, side=LEFT)
        self.entry_frame.pack()
        self.observation = Label(self.root, text='observations will appear here', wraplength=640, font = small_font)
        self.observation.pack()
        self.reward = Label(self.root, text='rewards will appear here', wraplength=640, font = small_font)
        self.reward.pack()
        self.mouse_event = self.prev_mouse_event = None
        
    def runMission( self, mission_spec, mission_record_spec, action_space ):
        '''Sets a mission running.
        
        Parameters:
        mission_spec : MissionSpec instance, specifying the mission.
        mission_record_spec : MissionRecordSpec instance, specifying what should be recorded.
        action_space : string, either 'continuous' or 'discrete' that says which commands to generate.
        '''
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
        self.world_state = None
        self.action_space = action_space
        total_reward = 0

        if mission_spec.isVideoRequested(0):
            self.canvas.config( width=mission_spec.getVideoWidth(0), height=mission_spec.getVideoHeight(0) )

        try:
            self.agent_host.startMission( mission_spec, mission_record_spec )
        except RuntimeError as e:
            tkMessageBox.showerror("Error","Error starting mission: "+str(e))
            return

        print "Waiting for the mission to start",
        self.world_state = self.agent_host.peekWorldState()
        while not self.world_state.is_mission_running:
            sys.stdout.write(".")
            time.sleep(0.1)
            self.world_state = self.agent_host.peekWorldState()
            for error in self.world_state.errors:
                print "Error:",error.text
        print
        if mission_spec.isVideoRequested(0) and action_space == 'continuous':
            self.canvas.config(cursor='none') # hide the mouse cursor while over the canvas
            self.canvas.event_generate('<Motion>', warp=True, x=self.canvas.winfo_width()/2, y=self.canvas.winfo_height()/2) # put cursor at center
            self.root.after(50, self.update)
        self.canvas.focus_set()

        while self.world_state.is_mission_running:
            self.world_state = self.agent_host.getWorldState()
            if self.world_state.number_of_observations_since_last_state > 0:
                self.observation.config(text = self.world_state.observations[0].text )
            if mission_spec.isVideoRequested(0) and self.world_state.number_of_video_frames_since_last_state > 0:
                frame = self.world_state.video_frames[-1]
                image = Image.frombytes('RGB', (frame.width,frame.height), str(frame.pixels) )
                photo = ImageTk.PhotoImage(image)
                self.canvas.delete("all")
                self.canvas.create_image(frame.width/2, frame.height/2, image=photo)
                self.canvas.create_line( frame.width/2 - 5, frame.height/2, frame.width/2 + 6, frame.height/2, fill='white' )
                self.canvas.create_line( frame.width/2, frame.height/2 - 5, frame.width/2, frame.height/2 + 6, fill='white' )
                self.root.update()
            for reward in self.world_state.rewards:
                total_reward += reward.getValue()
            self.reward.config(text = str(total_reward) )
            time.sleep(0.01)
        if mission_spec.isVideoRequested(0) and action_space == 'continuous':
            self.canvas.config(cursor='arrow') # restore the mouse cursor
        print 'Mission stopped'
        if not self.agent_host.receivedArgument("test"):
            tkMessageBox.showinfo("Ended","Mission has ended. Total reward: " + str(total_reward) )
        self.root.destroy()
        
    def onSendCommand(self):
        '''Called when user presses the 'send' button or presses 'Enter' while the command entry box has focus.'''
        self.agent_host.sendCommand(self.command_entry.get())
        self.command_entry.delete(0,END)

    def update(self):
        '''Called at regular intervals to poll the mouse position to send continuous commands.'''
        if self.action_space == 'continuous': # mouse movement only used for continuous action space
            if self.world_state and self.world_state.is_mission_running:
                if self.mouse_event and self.prev_mouse_event:
                        rotation_speed = 0.1
                        turn_speed = ( self.mouse_event.x - self.prev_mouse_event.x ) * rotation_speed
                        pitch_speed = ( self.mouse_event.y - self.prev_mouse_event.y ) * rotation_speed
                        self.agent_host.sendCommand( 'turn '+str(turn_speed) )
                        self.agent_host.sendCommand( 'pitch '+str(pitch_speed) )
                if self.mouse_event:
                    if os.name == 'nt': # (moving the mouse cursor only seems to work on Windows)
                        self.canvas.event_generate('<Motion>', warp=True, x=self.canvas.winfo_width()/2, y=self.canvas.winfo_height()/2) # put cursor at center
                        self.mouse_event.x = self.canvas.winfo_width()/2
                        self.mouse_event.y = self.canvas.winfo_height()/2
                    self.prev_mouse_event = self.mouse_event
        if self.world_state.is_mission_running:
            self.root.after(50, self.update)

    def onMouseMoveInCanvas(self, event):
        '''Called when the mouse moves inside the canvas.'''
        self.mouse_event = event
      
    def onLeftMouseDownInCanvas(self, event):
        '''Called when the left mouse button is pressed on the canvas.'''
        self.canvas.focus_set()
        self.agent_host.sendCommand( 'attack 1' )
      
    def onLeftMouseUpInCanvas(self, event):
        '''Called when the left mouse button is released on the canvas.'''
        self.canvas.focus_set()
        self.agent_host.sendCommand( 'attack 0' )
      
    def onRightMouseDownInCanvas(self, event):
        '''Called when the right mouse button is pressed on the canvas.'''
        self.canvas.focus_set()
        self.agent_host.sendCommand( 'use 1' )
      
    def onRightMouseUpInCanvas(self, event):
        '''Called when the right mouse button is released on the canvas.'''
        self.canvas.focus_set()
        self.agent_host.sendCommand( 'use 0' )
      
    def onKeyInCommandEntry(self, event):
        '''Called when a key is pressed when the command entry box has focus.'''
        if event.char == '\r':
            self.onSendCommand()
            self.canvas.focus_set() # move focus back to the canvas to continue moving
           
    def onKeyPressInCanvas(self, event):
        '''Called when a key is pressed when the canvas has focus.'''
        char_map = { 'w':'move 1', 'a':'strafe -1', 's':'move -1', 'd':'strafe 1', ' ':'jump 1' }
        keysym_map = { 'continuous': { 'Left':'turn -1', 'Right':'turn 1', 'Up':'pitch -1', 'Down':'pitch 1', 'Shift_L':'crouch 1',
                                       'Shift_R':'crouch 1', 
                                       '1':'hotbar.1 1', '2':'hotbar.2 1', '3':'hotbar.3 1', '4':'hotbar.4 1', '5':'hotbar.5 1',
                                       '6':'hotbar.6 1', '7':'hotbar.7 1', '8':'hotbar.8 1', '9':'hotbar.9 1' },
                       'discrete':   { 'Left':'turn -1', 'Right':'turn 1', 'Up':'move 1', 'Down':'move -1', 
                                       '1':'hotbar.1 1', '2':'hotbar.2 1', '3':'hotbar.3 1', '4':'hotbar.4 1', '5':'hotbar.5 1',
                                       '6':'hotbar.6 1', '7':'hotbar.7 1', '8':'hotbar.8 1', '9':'hotbar.9 1' } }
        if event.char == '/':
            self.command_entry.focus_set() # interlude to allow user to type command
        elif event.char.lower() in char_map:
            self.agent_host.sendCommand( char_map[ event.char.lower() ] )
        elif event.keysym in keysym_map[self.action_space]:
            self.agent_host.sendCommand( keysym_map[self.action_space][ event.keysym ] )

    def onKeyReleaseInCanvas(self, event):
        '''Called when a key is released when the command entry box has focus.'''
        char_map = { 'w':'move 0', 'a':'strafe 0', 's':'move 0', 'd':'strafe 0', ' ':'jump 0' }
        keysym_map = { 'Left':'turn 0', 'Right':'turn 0', 'Up':'pitch 0', 'Down':'pitch 0', 'Shift_L':'crouch 0', 'Shift_R':'crouch 0', 
                       '1':'hotbar.1 0', '2':'hotbar.2 0', '3':'hotbar.3 0', '4':'hotbar.4 0', '5':'hotbar.5 0',
                       '6':'hotbar.6 0', '7':'hotbar.7 0', '8':'hotbar.8 0', '9':'hotbar.9 0' }
        if event.char.lower() in char_map:
            self.agent_host.sendCommand( char_map[ event.char.lower() ] )
        elif event.keysym in keysym_map:
            self.agent_host.sendCommand( keysym_map[ event.keysym ] )

#action_space = 'discrete'
action_space = 'continuous'
my_mission = MalmoPython.MissionSpec()
my_mission.requestVideo( 640, 480 )
my_mission.timeLimitInSeconds( 30 )
my_mission.allowAllChatCommands()
my_mission.allowAllInventoryCommands()
my_mission.setTimeOfDay( 1000, False )
my_mission.observeChat()
my_mission.observeGrid( -1, -1, -1, 1, 1, 1, 'grid' )
my_mission.observeHotBar()
my_mission.drawBlock( 5, 226, 5, 'gold_block' )
my_mission.rewardForReachingPosition( 5.5, 227, 5.5, 100, 0.1 )
my_mission.endAt( 5.5, 227, 5.5, 0.1 )
my_mission.startAt( 0.5, 227, 0.5 )
if action_space=='discrete':
    my_mission.removeAllCommandHandlers()
    my_mission.allowAllDiscreteMovementCommands()

my_mission_record = MalmoPython.MissionRecordSpec('./hac_saved_mission.tgz')
my_mission_record.recordCommands()
my_mission_record.recordMP4( 20, 400000 )
my_mission_record.recordRewards()
my_mission_record.recordObservations()

HumanAgentHost( sys.argv, my_mission, my_mission_record, action_space )
