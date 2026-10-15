# Used camera module:
# https://github.com/cnadler86/micropython-camera-API

from camera import Camera, GrabMode, PixelFormat, FrameSize

cam = None

try:
    cam = Camera(
                data_pins=[16,17,18,8,9,10,11,12],
                vsync_pin=6,
                href_pin=7,
                sda_pin=4,
                scl_pin=5,
                pclk_pin=13,

                xclk_pin=-1,
                powerdown_pin=-1,
                reset_pin=-1,

                pixel_format=PixelFormat.JPEG,
                frame_size=FrameSize.CIF,
                jpeg_quality=90,
                fb_count=2,
                grab_mode=GrabMode.LATEST)

    print("[CAMERA] initialization is OK")

except Exception as e:
    print("[CAMERA] initialization ERROR:", repr(e))

def make_photo(filename=''):

    if filename == '' or cam is None:
        return False

    try:
        img = bytes(cam.capture()) 

        with open(filename, "wb") as f:
            f.write(img)

        cam.free_buffer()
        f.close()
        return True
    
    except:
        return False
