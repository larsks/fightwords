This directory contains MicroPython code to display PBM images on an OLED display.

1. Convert your images to PBM format using `png2pbm.sh`.

2. Copy the Python code and the images to your MicroPython device:

    ```
    mpremote cp *py :
    mpremote mkdir pbms
    mpremote cp pbms/* :pbms
    ```

3. Reboot the MicroPython device
