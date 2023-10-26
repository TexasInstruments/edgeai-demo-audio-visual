# Edge AI Audio Visual Demonstration

This repository hosts source code for an Edge AI demo on TI processors, focused on audio and visual processing.

This demo shows an audio-visual system in the form of a video conferencing front end. It shows side-by-side audio and vision processing to infer meaning from the raw signals that come in. Audio data is processed on the CPU. Vision and imagery is processed using a variety of hardware accelerators, including an ISP (VISS), a downscaling engine (MSC), and a deep learning accelerator (C7xMMA).


This demo has been validated on the AM62A running the 9.0.0 Edge AI Linux SDK. It is expected to run equivalently well on other AM6xA / Edge AI processors from TI, like the TDA4VM, AM68A, and AM69A

## How to run this demo

Note: this demo borrows heavily from the [edgeai-keyword-spotting](https://github.com/TexasInstruments/edgeai-keyword-spotting) and [edgeai-gst-apps-retail-checkout](https://github.com/TexasInstruments/edgeai-gst-apps-retail-checkout) projects for running a keyword spotting neural network on microphone audio and constructing a image-processing gstreamer pipeline, respectively.

1. Obtain an EVM for the AM6xA processor of choice, e.g. the [AM62A Starter Kit](https://www.ti.com/tool/SK-AM62A-LP)
2. Flash an SD card with the Edge AI SDK (Linux) by following the quick start guide [(Quick start for AM62A)](https://dev.ti.com/tirex/explore/node?node=A__AQniYj7pI2aoPAFMxWtKDQ__am62ax-devtools__FUz-xrs__LATEST)
3. Login to the device over a serial or SSH connection. A network connection is required to setup this demo
4. Clone this repository to the device using git.  
  * If the EVM is behind a proxy, first set the HTTPS_PROXY environment variable and then add it to git: `git config --global https.proxy $HTTPS_PROXY`
5. Run the [audio_setup.sh](./audio_setup.sh) script to download, build, and install libportaudio, pyaudio, and librosa to the device. This will fail if the network or proxy are not configured.
6. Plug in a USB microphone
7. Run the [detect_microphone.py](./detect_microphone.py) script to recognize which device index to use in Linux. If this is not 1, provide this as an argument with the -a tag when running the run_demo.sh script later
  * This may print many additional lines and warnings -- these can be safely ignored if audio dependencies were installed.
8. Using an IMX219 camera, enable the DTBO for this camera type by adding a line uEnv.txt using instructions on [dev.ti.com page for "Evaluating Linux -> Camera" in AM62A academy](https://dev.ti.com/tirex/explore/node?node=A__ATmvgyzeqCfCvoHoyFGZGw__AM62A-ACADEMY__WeZ9SsL__LATEST)
9. Reboot the board so the device tree overlay is applied
10. Once confirmed the IMX219 is enabled (it will show in the terminal when a shell is opened), run the [setup_imx219-2mp.sh](./setup_imx219-2mp.sh) script to set 2 MP mode for 1640x1232 resolution
11. Run the run_demo.sh script. 
  * Errors like seg-fault will occur from choosing the wrong device_index for the microphone

## Resources and Help

* [Support Forums](https://e2e.ti.com)
* [Edge AI Resources FAQ](https://e2e.ti.com/support/processors-group/processors/f/processors-forum/1236957/faq-edge-ai-studio-edge-ai-resources-for-am6xa-socs)
* [TI Edge AI Github](https://github.com/TexasInstruments/edgeai)
* [Edge AI Studio cloud-based resources](https://dev.ti.com/edgeaistudio/)