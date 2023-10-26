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
Main application for vision and keyword spotting application. 

This creates two processes - one for gstreamer and vision, the other for audio processing.
The audio processing pipeline provides the output for command / speech recognition via a shared queue.

Use the -h tag for displaying the command line options 
'''


import os, time
from pprint import pprint
import numpy as np
import yaml
import threading
import argparse
import math
import multiprocessing as mp
import queue
from collections import deque
import cv2 as cv

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstApp, GLib, GObject
Gst.init(None)

import gst_configs, model_runner, display, utils
import kws_matchbox as kws
import command_interpreter

# global variables to help control the GST thread
stop_threads = False
infer_thread = None


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--camera', default='usb-1080p', help='name of camera type to use. options are usb-720p from logitech, usb-1080p (c920 or c922 from logitech), and IMX219 (RPi cam v2)')
    parser.add_argument('-m', '--modeldir', default='./model/', help='location of the model directory. Assumed to have dataset.yaml, param.yaml, model as model.onnx, and subdir for artifacts. See typical format of directories from /opt/model_zoo for example')
    parser.add_argument('-d', '--device', default='/dev/video2', help="location of the camera device under /dev")
    parser.add_argument('-o', '--output-dimensions', default='1280x720', help="Resolution of the output display in WxH format, e.g. 1920x1080")
    parser.add_argument('-a', '--audio-device', default=1, type=int, help='The device channel index for your microphone. This is typically on starter kit EVMs. Run the detect_microphone.py script to see which microphones are connected')

    args = parser.parse_args()
    
    return args

def print_stats(stats):
    '''
    Print some runtime stats related to total time, preprocessing, and postprocessing
    '''
    print('\nRan %i frames' % stats['count'])
    mean_inf = stats['total_pre_stage_s'] / stats['count']
    mean_out = stats['total_output_stage_s'] / stats['count']
    mean_overall = stats['total_infer_frame'] / stats['count']
    fps = 1/mean_overall
    std_inf = math.sqrt(stats['total_pre_stage_sq'] / stats['count'] - mean_inf**2)
    std_out = math.sqrt(stats['total_output_stage_sq'] / stats['count'] - mean_out**2)
    print('**** Runtime Stats ****')
    print('---- Pull input time (ms): avg %d +- %d (min to max: %d to %d)' % (mean_inf*1000, std_inf*1000, stats['total_pre_stage_min']*1000, stats['total_pre_stage_max']*1000))
    print('---- Output (draw, post-proc) time (ms): avg %d +- %d' % (mean_out*1000, std_out*1000))
    print('---- FPS: %.02f' % fps)
    print("-----------------------\n")


def application_thread(gst_conf:gst_configs.GstBuilder, model_obj:model_runner.ModelRunner, display_obj:display.DisplayDrawer, categories, args, input_queue):
    '''
    This is where application code between appsink and appsrc code lives
    '''
    print("waiting until audio thread gives something:")
    try:
        kws_output = input_queue.get(block=True)
        print('\n***\ngot some kws output...ready to start the rest the vision pipeline!\n***\n')
        print(kws_output)
    except: pass

    last_commands = deque(maxlen=5)
    commander = command_interpreter.CommandInterpreter()

    if not hasattr(gst_conf, 'gst_str'): gst_conf.build_gst_strings(model_obj)

    gst_conf.start_gst()
    
    #we'll collect some statistics on where time is spent in the application
    stats = {'count':0, 'total_pre_stage_s':0, 'total_output_stage_s':0, 'total_pre_stage_sq':0, 'total_output_stage_sq':0, 'total_pre_stage_min':100000, 'total_pre_stage_max':-1, 'total_infer_frame':0}

    #run to init and output frame. pushing images alleviates race condition between the pipelines and prevents hanging
    output_frame = display_obj.make_frame_init()
    t_loop = time.time()

    global stop_threads 
    while not stop_threads:
        #push an image from the last iteration first so we're able to create the display output immediately
        display_obj.push_to_display(output_frame)
        # print('pull GST buffers')
        t_start_loop = time.time()
        sample_tensor, _ = gst_conf.pull_sample(gst_conf.app_in_tensor, loop=False)
        if not sample_tensor: continue

        sample_image, struct_image = gst_conf.pull_sample(gst_conf.app_in_image, loop=False)
        if not sample_image: continue

        # print('got GST buffers in app code')

        # tensor is the output of dlinferer. If so, format is model dependent. View tidlpostproc and tidlinferer to  see how this structure is encoded into a buffer. If there are multiple tensors, there will be offsets. Values below are specific to mobilvenetv2SSD-lite 
        t_pre_draw = time.time()

        #decode the tensor. Model dependent
        infer_output = model_obj.decode_output_tensor(sample_tensor)
        #resize the bounding boxes from the model to match the image dimensions. Helps with visualization logic
        infer_output = model_obj.resize_boxes(infer_output, struct_image.get_value("height"), struct_image.get_value("width"))

        try:
            #pull keyword spotting output from the queue, but don't wait for it
            kws_output = input_queue.get_nowait()

            if np.max(kws_output[0]) > kws.AudioInference.LOGIT_THRESHOLD:
                max_conf = int(np.argmax(kws_output[0]))
                command = None if max_conf < 0 else kws_output[1][max_conf]
                last_commands.append(command)
                print(last_commands)
        except queue.Empty: pass

        action = commander.interpret_commands(last_commands)

        # reshape data buffer to match the dimensions
        input_image = gst_conf.format_image_from_sample(sample_image, struct_image)
        # cv.imwrite('from_gst.png', input_image)
        t_post_proc = time.time()

        # create the output frame; gets pushed at top of loop
        output_frame = display_obj.make_frame(input_image, infer_output, categories, model_obj, action)
        t_final = time.time()
        
        #collect some stats    
        stats['count'] += 1
        stats['total_pre_stage_s'] += t_pre_draw - t_start_loop
        stats['total_pre_stage_min'] = min(t_pre_draw - t_start_loop, stats['total_pre_stage_min'])
        stats['total_pre_stage_max'] = max(t_pre_draw - t_start_loop, stats['total_pre_stage_max'])

        stats['total_pre_stage_sq'] += (t_pre_draw - t_start_loop)**2
        stats['total_output_stage_s'] += t_final - t_pre_draw
        stats['total_output_stage_sq'] += (t_final - t_pre_draw)**2

        stats['total_infer_frame'] += (time.time() - t_loop)
        t_loop = time.time()
        # print_stats(stats)

    if stats['count'] > 0:
        print_stats(stats)

def kws_thread(output_queue, device_index):
    audio = kws.AudioInference(modeldir='.', modelname='matchboxnet.onnx', device_index=device_index, output_queue=output_queue)
    audio.setup()

    while (audio.input_stream.is_active()): 
        # print something so developer knows the thread is alive
        print('audio still running...')
        time.sleep(5)

    audio.stop()


def main():
    args = parse_args()
    
    # camera parameters and information assumed based on device in CLI args
    cam_params = gst_configs.CamParams(args.camera, device=args.device)
    # configure display output information
    display_dimensions = args.output_dimensions.split('x')
    display_width = int(display_dimensions[0])
    display_height = int(display_dimensions[1])
    display_obj = display.DisplayDrawer(display_width, display_height,         aspect_ratio=4/3)

    #load model's params'yaml file
    modeldir = args.modeldir
    paramsfile = os.path.join(modeldir, 'param.yaml')
    model_params = yaml.safe_load(open(paramsfile, 'r'))

    #the set of classes/categories recognized by the model
    categories = utils.get_categories(modeldir)

    # setup the model for inference. Parameters used by gst_config
    model_obj = model_runner.ModelRunner(modeldir, paramsfile=paramsfile)
    model_obj.load_model() #load model to get info about input data type
    
    #create the gstreamer pipeline based on model and camera parameters
    gst_conf = gst_configs.GstBuilder(model_params, cam_params, display_obj) 
    gst_conf.build_gst_strings(model_obj)
    # start the pipeline and saves references to appsrc/appsink
    gst_conf.setup_gst_appsrcsink()

    display_obj.set_gst_info(gst_conf.app_out, gst_conf.gst_caps)
    
    av_queue = mp.Queue(maxsize=4)

    global stop_threads
    stop_threads = False
    # fork an application thread to make KB interrupts easier to catch
    app_thread = threading.Thread(target=application_thread, args=[gst_conf, model_obj, display_obj, categories, args, av_queue])
    app_thread.start()

    #fork a process to allow parallel processing
    kws_process = mp.Process(target=kws_thread, args=[av_queue, args.audio_device])
    kws_process.start()

    try: 
        while not stop_threads:
            time.sleep(2)
    except KeyboardInterrupt:
        print('KB shortcut caught')
        stop_threads = True

    gst_conf.pipe.set_state(Gst.State.PAUSED)
    gst_conf.out_pipe.set_state(Gst.State.PAUSED)
    print('paused pipe; waiting gst thread to join')
    app_thread.join()
    print('exiting...')

if __name__ == '__main__':
    main()