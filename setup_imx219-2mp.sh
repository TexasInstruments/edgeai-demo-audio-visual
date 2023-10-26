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
GREEN='\033[0;32m'
NOCOLOR='\033[0m'


declare -A ALL_UB960_FMT_STR
declare -A ALL_CDNS_FMT_STR
declare -A ALL_CSI2RX_FMT_STR

setup_routes(){

    OV2312_CAM_FMT='[fmt:SBGGI10_1X10/1600x1300 field: none]'
    IMX390_CAM_FMT='[fmt:SRGGB12_1X12/1936x1100 field: none]'

    for i in "${!ALL_UB960_FMT_STR[@]}"
    do
        id="$(cut -d',' -f1 <<<"$i")"
        name="$(cut -d',' -f2 <<<"$i")"
        # UB960 ROUTING & FORMATS
        media-ctl -d $id -R "'$name' [${ALL_UB960_FMT_STR[$i]}]"

        for name in `media-ctl -d $id -p | grep entity | grep ov2312 | cut -d ' ' -f 5`; do
            UB953_NAME=`media-ctl -d $id -p -e "ov2312 $name" | grep ub953 | cut -d "\"" -f 2`
            UB960_NAME=`media-ctl -d $id -p -e "$UB953_NAME" | grep ub960 | cut -d "\"" -f 2`
            UB960_PAD=`media-ctl -d $id -p -e "$UB953_NAME" | grep ub960 | cut -d : -f 2 | awk '{print $1}'`
            media-ctl -d $id -V "'$UB960_NAME':$UB960_PAD/0 $OV2312_CAM_FMT"
            media-ctl -d $id -V "'$UB960_NAME':$UB960_PAD/1 $OV2312_CAM_FMT"
        done

        for name in `media-ctl -d $id -p | grep entity | grep imx390 | cut -d ' ' -f 5`; do
            UB953_NAME=`media-ctl -d $id -p -e "imx390 $name" | grep ub953 | cut -d "\"" -f 2`
            UB960_NAME=`media-ctl -d $id -p -e "$UB953_NAME" | grep ub960 | cut -d "\"" -f 2`
            UB960_PAD=`media-ctl -d $id -p -e "$UB953_NAME" | grep ub960 | cut -d : -f 2 | awk '{print $1}'`
            media-ctl -d $id -V "'$UB960_NAME':$UB960_PAD $IMX390_CAM_FMT"
        done

    done

    # CDNS ROUTING
    for i in "${!ALL_CDNS_FMT_STR[@]}"
    do
        id="$(cut -d',' -f1 <<<"$i")"
        name="$(cut -d',' -f2 <<<"$i")"
        # CDNS ROUTING & FORMATS
        media-ctl -d $id -R "'$name' [${ALL_CDNS_FMT_STR[$i]}]"

        for name in `media-ctl -d $id -p | grep entity | grep ov2312 | cut -d ' ' -f 5`; do
            UB953_NAME=`media-ctl -d $id -p -e "ov2312 $name" | grep ub953 | cut -d "\"" -f 2`
            UB960_NAME=`media-ctl -d $id -p -e "$UB953_NAME" | grep ub960 | cut -d "\"" -f 2`
            UB960_PAD=`media-ctl -d $id -p -e "$UB953_NAME" | grep ub960 | cut -d : -f 2 | awk '{print $1}'`
            CSI_PAD0=`media-ctl -d $id -p -e "$UB960_NAME" | grep $UB960_PAD/0.*[ACTIVE] | cut -d "/" -f 3 | awk '{print $1}'`
            CSI_PAD1=`media-ctl -d $id -p -e "$UB960_NAME" | grep $UB960_PAD/1.*[ACTIVE] | cut -d "/" -f 3 | awk '{print $1}'`
            CSI_BRIDGE_NAME=`media-ctl -d $id -p -e "$UB960_NAME" | grep csi-bridge | cut -d "\"" -f 2`
            media-ctl -d $id -V "'$CSI_BRIDGE_NAME':0/$CSI_PAD0 $OV2312_CAM_FMT"
            media-ctl -d $id -V "'$CSI_BRIDGE_NAME':0/$CSI_PAD1 $OV2312_CAM_FMT"
        done

        for name in `media-ctl -d $id -p | grep entity | grep imx390 | cut -d ' ' -f 5`; do
            UB953_NAME=`media-ctl -d $id -p -e "imx390 $name" | grep ub953 | cut -d "\"" -f 2`
            UB960_NAME=`media-ctl -d $id -p -e "$UB953_NAME" | grep ub960 | cut -d "\"" -f 2`
            UB960_PAD=`media-ctl -d $id -p -e "$UB953_NAME" | grep ub960 | cut -d : -f 2 | awk '{print $1}'`
            CSI_PAD=`media-ctl -d $id -p -e "$UB960_NAME" | grep $UB960_PAD/.*[ACTIVE] | cut -d "/" -f 3 | awk '{print $1}'`
            CSI_BRIDGE_NAME=`media-ctl -d $id -p -e "$UB960_NAME" | grep csi-bridge | cut -d "\"" -f 2`
            media-ctl -d $id -V "'$CSI_BRIDGE_NAME':0/$CSI_PAD $IMX390_CAM_FMT"
        done
    done

    # CSI2RX ROUTING
    for i in "${!ALL_CSI2RX_FMT_STR[@]}"
    do
        id="$(cut -d',' -f1 <<<"$i")"
        name="$(cut -d',' -f2 <<<"$i")"
        media-ctl -d $id -R "'$name' [${ALL_CSI2RX_FMT_STR[$i]}]"
    done

}

setup_imx219(){
    IMX219_CAM_FMT='[fmt:SRGGB10_1X10/1640x1232]'
    count=0
    for media_id in {0..1}; do
    for name in `media-ctl -d $media_id -p | grep entity | grep imx219 | cut -d ' ' -f 5`; do
        CAM_SUBDEV=`media-ctl -d $media_id -p -e "imx219 $name" | grep v4l-subdev | awk '{print $4}'`
        media-ctl -d $media_id --set-v4l2 ''"\"imx219 $name\""':0 '$IMX219_CAM_FMT''

        CSI_BRIDGE_NAME=`media-ctl -d $media_id -p -e "imx219 $name" | grep csi-bridge | cut -d "\"" -f 2`
        CSI2RX_NAME=`media-ctl -d $media_id -p -e "$CSI_BRIDGE_NAME" | grep "ticsi2rx\"" | cut -d "\"" -f 2`
        CSI2RX_CONTEXT_NAME="$CSI2RX_NAME context 0"

        CAM_DEV=`media-ctl -d $media_id -p -e "$CSI2RX_CONTEXT_NAME" | grep video | awk '{print $4}'`
        CAM_DEV_NAME=/dev/video-rpi-cam$count

        CAM_SUBDEV_NAME=/dev/v4l-rpi-subdev$count

        ln -snf $CAM_DEV $CAM_DEV_NAME
        ln -snf $CAM_SUBDEV $CAM_SUBDEV_NAME

        echo -e "${GREEN}CSI Camera $media_id detected${NOCOLOR}"
        echo "    device = $CAM_DEV_NAME"
        echo "    name = imx219"
        echo "    format = $IMX219_CAM_FMT"
        echo "    subdev_id = $CAM_SUBDEV_NAME"
        echo "    isp_required = yes"
        count=$(($count + 1))
    done
    done
}


setup_USB_camera(){
    ls /dev/v4l/by-path/*usb*video-index0 > /dev/null 2>&1
    if [ "$?" == "0" ]; then
        USB_CAM_ARR=(`ls /dev/v4l/by-path/*usb*video-index0`)
        count=0
        for i in ${USB_CAM_ARR[@]}
        do
            USB_CAM_DEV=`readlink -f $i`
            USB_CAM_NAME=/dev/video-usb-cam$count
            ln -snf $USB_CAM_DEV $USB_CAM_NAME
            echo -e "${GREEN}USB Camera $count detected${NOCOLOR}"
            echo "    device = $USB_CAM_NAME"
            echo "    format = jpeg"
            count=$(($count + 1))
        done
    fi
}

setup_USB_camera
setup_imx219
setup_routes
