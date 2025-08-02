import framebuf

def read_pbm_p4(filename):
    with open(filename, 'rb') as f:
        # Read magic number (P4)
        magic = f.readline().strip()
        if magic != b'P4':
            raise ValueError("Not a PBM P4 file")

        # Skip comments
        while True:
            line = f.readline().strip()
            if not line.startswith(b'#'):
                break
        
        # Read dimensions
        width, height = [int(val) for val in line.split()]

        # Read binary image data
        data = bytearray(f.read())

    # Create a FrameBuffer object (assuming MONO_HLSB for horizontal scan, MSB first)
    fbuf = framebuf.FrameBuffer(data, width, height, framebuf.MONO_HLSB)
    return fbuf, width, height
