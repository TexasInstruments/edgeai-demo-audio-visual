#  Copyright (C) 2023 Texas Instruments Incorporated - http://www.ti.com/
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
'''
This class creates handles the display and visualization by modifying input frames and pushing an output frame to gstreamer. 

Intended output display:
+------------------------------+----------+
|                              |          |
|                              |          |
|                              |  stats   |
|                              |  &       |
|  frame w/ post process       |  app     |
|  & visualization             |  info    |
|                              |          |
|                              |          |
|                              |          |
+------------------------------+----------+
|                                         |
|        performance stats/load           |
|                                         |
+-----------------------------------------+

The top two components of the display shown above will be made in this file. The bottom portion is blank so that tiperfoverlay can add performance overlay
'''


import numpy as np
import cv2 as cv
import time
import utils


import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstApp, GLib, GObject
Gst.init(None)

from command_interpreter import Actions

class DisplayDrawer():
    '''
    Class to the output display. This is written primarily for 1920 x 1080 display, but should also scale to other sizes

    Performance stats should take up 20% of the image at the bottom, but have hard limit of height between 50 and 250 pixels. See tiperfoverlay gst plugin for source of this.

    '''
    def __init__(self, display_width=1920, display_height=1080, image_scale=0.8, aspect_ratio=16/9):
        self.display_width = display_width
        self.display_height = display_height
        self.image_scale = image_scale

        # scale the upper left port of the screen 
        self.image_height = int(display_height * image_scale)
        self.image_width = int(self.image_height * aspect_ratio)
        # self.image_width = int(display_width * image_scale)
        self.info_panel_width = display_width - self.image_width
        self.info_panel_height = self.image_height
        self.perf_width = display_width
        self.perf_height = display_height - self.image_height


    def set_gst_info(self, app_out, gst_caps): 
        '''
        Set output caps and hold onto a reference for the appsrc plugin that interfaces from here to the final output sink (by default, kmssink.. see gst_configs.py)
        '''
        self.gst_app_out = app_out
        self.gst_caps = gst_caps
        self.gst_app_out.set_caps(self.gst_caps)


    def push_to_display(self, image):
        '''
        Push an image to the display through the appsrc

        param image: and image whose dimensions and pixel format matches self.gst_caps
        '''

        buffer = Gst.Buffer.new_wrapped(image.tobytes())

        ret = self.gst_app_out.push_buffer(buffer)
      
    def make_frame_init(self):
        '''
        Make an initial frame to push immediately. This is intentionally blank
        '''
        return np.zeros((self.display_height, self.display_width, 3), dtype=np.uint8)
    
    def make_frame_passthrough(self, input_image):
        # processed_image = self.make_depth_map(input_image, infer_output)

        frame = np.zeros((self.display_height, self.display_width, 3), dtype=np.uint8)
        frame[0:self.image_height, 0:self.image_width] = input_image
        # frame[0:self.image_height, self.image_width:] = 255

        return frame

    def make_frame(self, input_image, infer_output, categories, model_obj, action):
        '''
        Use the output information from the tidlinferer plugin (after reformatting to convenient shape)
            to write some useful information onto various portions of the screen
        
        input image: HxWxC numpy array
        infer_output: tensor/2d array of shape num_boxes x 6, where the 6 values are x1,y1,x2,y2,score, label
        categories: in same format as dataset.yaml, a mapping of class labels to class names (strings)
        model_obj: the ModelRunner object associated with the model being run with tidlinferer
        '''

        processed_image, faces = self.draw_bounding_boxes(input_image.copy(), infer_output, categories)
        t1 = time.time()
        visualization, image_coord_ul, viz_size = self.create_visualization(processed_image, action)
        face_pane = self.create_face_pane(input_image, faces, image_coord_ul, viz_size)
        t2 = time.time()
        print("making viz frame time: %.3f ms" % ((t2-t1)*1000))

        frame = np.zeros((self.display_height, self.display_width, 3), dtype=np.uint8)
        frame[0:self.image_height, 0:self.image_width] = visualization
        frame[0:self.image_height, self.image_width:] = face_pane

        return frame
    
    def draw_bounding_boxes(self, image, boxes_tensor, categories, viz_thres=0.6):
        '''
        Draw bounding boxes with classnames onto the 
        
        Each box in the tensor expected to be x1,y1,x2,y2,score,class-label.

        '''
        objects = []
        for box in boxes_tensor:
            score = box[4]
            label = box[5]

            if score > viz_thres:
                class_name = categories[int(label)]['name']
                x1,y1,x2,y2 = box.astype(np.int32)[:4]
                # print(box)
                cv.rectangle(image, (x1,y1), (x2,y2), color=(0, 255, 255), thickness=4)
                # cv.putText(image, class_name, (x1,y1), cv.FONT_HERSHEY_SIMPLEX, 0.75, color=(0, 255, 255), thickness=2)
                objects.append((x1,y1,x2,y2, class_name))

        return image, objects

    def create_visualization(self, input_image, action):
        # print('viz input size: ' + str(input_image.shape))
        print(str(action))
        size=None
        if action == Actions.PASSTHROUGH:
            # viz_image = cv.resize(input_image, (self.image_width, self.image_height), interpolation=cv.INTER_CUBIC)
            size = input_image.shape
            viz_image = cv.resize(input_image, (self.image_width, self.image_height), interpolation=cv.INTER_AREA)
            point = (0,0)
        elif action == Actions.LEFT:
            x = 0
            y = int((input_image.shape[0] - self.image_height) / 2)
            point=(x,y)
            viz_image = input_image[y:y+self.image_height, x:x+self.image_width]
        elif action == Actions.RIGHT:
            x = int(input_image.shape[1] - self.image_width)
            y = int((input_image.shape[0] - self.image_height) / 2)
            point=(x,y)
            viz_image = input_image[y:y+self.image_height, x:x+self.image_width]
        elif action == Actions.UP:
            x = int((input_image.shape[1] - self.image_width) / 2)
            y = 0
            point=(x,y)
            viz_image = input_image[y:y+self.image_height, x:x+self.image_width]
        elif action == Actions.DOWN:
            x = int((input_image.shape[1] - self.image_width) / 2)
            y = int(input_image.shape[0] - self.image_height)
            point=(x,y)
            viz_image = input_image[y:y+self.image_height, x:x+self.image_width]
        elif action == Actions.ZOOM:
            x = int((input_image.shape[1] - self.image_width) / 2)
            y = int((input_image.shape[0] - self.image_height) / 2)
            point=(x,y)
            viz_image = input_image[y:y+self.image_height, x:x+self.image_width]
        elif action == Actions.OFF:
            viz_image = np.zeros((self.image_height, self.image_width, 3))
            point=(0,0)
            size=(0,0,3)
        # print('viz output size: ' + str(viz_image.shape))

        if viz_image.shape[0] != self.image_height or viz_image.shape[1] != self.image_width:
            size = viz_image.shape
            viz_image = cv.resize(viz_image, (self.image_width, self.image_height), interpolation=cv.INTER_AREA)
        elif size is None:
            size = viz_image.shape


        return viz_image, point, size
    
    def create_face_pane(self, input_image, faces_list, crop_point, crop_size):
        '''
        Fill the info panel with crops of the faces to track people in the frame. The input image may be modified to only show a portion (e.g. the right side area or a zoomed in area) by cropping, so those cropping parameters are provided

        :param input_image: The entire input image, regardless of any cropping done based on a command/action 
        :param faces_list: A list of 4-element tuples (x1,y1,x2,y2) as bounding boxes of the output. The values will fit within the input_image, but not necessarily the cropped part of the image
        :param crop_point: Upper-left point representing where the output display will focus
        :param crop_size: The height and width of the area that the output display will focus on
        :return: An image destined for the right-pane of the output display, including individuals' faces resize to fit the region. By default, up to 9 faces can be shown. 
        '''
        faces_list = sorted(faces_list, key=lambda face: face[0]+face[1])
        face_pane = np.full(shape=[self.info_panel_height, self.info_panel_width, 3], fill_value=255, dtype=np.uint8)

        #create a list holding the images of faces that have already been cropped
        face_images = []

        #we'll increase the size of the area to include more of their head
        INCREASE_SIZE_SCALE = 0.2
        for face in faces_list:
            w = face[2] - face[0]
            h = face[3] - face[1]
            x1 = int(face[0] - w * INCREASE_SIZE_SCALE)
            x2 = int(face[2] + w * INCREASE_SIZE_SCALE)
            y1 = int(face[1] - h * INCREASE_SIZE_SCALE)
            y2 = int(face[3] + h * INCREASE_SIZE_SCALE)

            #check face points are within the vizualiatio post crop/resize
            if x1 >= crop_point[0] and \
                y1 >= crop_point[1] and \
                x2 <= crop_point[0] + crop_size[1] and \
                y2 <= crop_point[1] + crop_size[0]:

                # crop_locations = (x1, y1, x2, y2)
                # print(crop_locations)
                face_images.append(input_image[y1:y2, x1:x2])

        # define dimensions for how to place resized and cropped faces
        X_SPACING = 15
        Y_SPACING = 20
        FACE_SIZE = (150, 150) #x,y
        MAX_NUM_FACES = 9
        FACES_PER_ROW = 3
        FACES_PER_COLUMN = 3

        #draw rectangles to underline where faces can go
        x = X_SPACING
        y = Y_SPACING*2 + FACE_SIZE[1]
        for i in range(MAX_NUM_FACES):
            cv.rectangle(face_pane, (x,y), (x+FACE_SIZE[0],y),color=(0,0,0), thickness=2)
            y += Y_SPACING + FACE_SIZE[1]
            if i % FACES_PER_COLUMN == FACES_PER_COLUMN - 1:
                x += X_SPACING + FACE_SIZE[0]
                y = Y_SPACING*2 + FACE_SIZE[1]

        x = X_SPACING
        y = Y_SPACING*2
        for i, face in enumerate(face_images):
            #copy the face area, resize, and add to the output image
            copy_face = cv.resize(face.copy(), FACE_SIZE, interpolation=cv.INTER_AREA)
            face_pane[y:y+FACE_SIZE[1], x:x+FACE_SIZE[0]] = copy_face
            cv.putText(face_pane, f'Attendee {i+1}', (x,y-3), cv.FONT_HERSHEY_SIMPLEX, 0.6, color=(0, 0, 0), thickness=1)
            y += Y_SPACING + FACE_SIZE[1]
            if i % FACES_PER_COLUMN == FACES_PER_COLUMN - 1:
                x += X_SPACING + FACE_SIZE[0]
                y = Y_SPACING*2
            if i >= MAX_NUM_FACES - 1: break

        return face_pane
