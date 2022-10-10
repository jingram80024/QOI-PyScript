import numpy as np
import struct
from PIL import Image

# encoding method tags
QOI_OP_RUN   = 0xc0
QOI_OP_INDEX = 0x00
QOI_OP_DIFF  = 0x40
QOI_OP_LUMA  = 0x80
QOI_OP_RGB   = 0xfe
QOI_OP_RGBA  = 0xff

FMT_STR = '>4sIIBB'
MAGIC = b'qoif'
QOI_END_MARKER = bytearray([0,0,0,0,0,0,0,1])

def _index_position(r: int, g: int, b: int, a: int) -> int:
    hash = (r * 3 + g * 5 + b * 7 + a * 11) % 64
    return hash

def _build_header(height: int, width: int, channels: int, colorspace: int) -> bytes:
    descriptors = (MAGIC, width, height, channels, colorspace)
    QOI_HEADER = struct.pack(FMT_STR, *descriptors)
    return QOI_HEADER

def encode(path: str) -> bytearray: # alter later to take in destination file path and save image there.
    # add error handling here for if user uploads file that pillow cannot handle
    # add exception if size is too big for RAM to handle? -> how big would that be?
    # see if Image class has mode info that can be used to set colorspace and channels
    image = Image.open(path)
    image_array = np.array(image)
    height, width, channels = image_array.shape
    colorspace = 0
    image_array = np.reshape(image_array, np.size(image_array))
    return encode_array(height, width, channels, colorspace, image_array)

def encode_array(height: int, width: int, channels: int, colorspace: int, color_stream: np.ndarray) -> bytearray:
    HASH_ARRAY = np.array([3, 5, 7, 11])
    r, g, b, a = (0, 0, 0, 255)
    pr, pg, pb, pa = (0, 0, 0, 255)
    run_count = 0
    index = np.full((64, 4), [0, 0, 0, 255], dtype='uint8')
    byte_stream = bytearray()
    byte_stream += _build_header(height, width, channels, colorspace)

    for offset in range(height * width):
        r = color_stream[offset * channels]
        g = color_stream[offset * channels + 1]
        b = color_stream[offset * channels + 2]
        if channels == 4: a = color_stream[offset * channels + 3]
    
        if [r, g, b, a] == [pr, pg, pb, pa]:
            run_count += 1
            if run_count == 62 or offset == (height * width):
                byte_stream += bytes([QOI_OP_RUN | run_count -1])
                run_count = 0

        else:
            if run_count > 0:
                byte_stream += bytes([QOI_OP_RUN | run_count - 1])
                run_count = 0
        
            hash = (np.dot(HASH_ARRAY, [r, g, b, a])) % 64
            if ([r, g, b, a] == index[hash]).all():
                byte_stream += bytes([QOI_OP_INDEX | hash])

            else:
                index[hash] = [r, g, b, a]

                if a != pa:
                    byte_stream += bytes([QOI_OP_RGBA, r, g, b, a])

                else:
                    dr, dg, db = ((int(r) - int(pr)), (int(g) - int(pg)), (int(b) - int(pb)))

                    if (dr >= -2 and dr <= 1) and (dg >= -2 and dg <= 1) and (db >= -2 and db <= 1):
                        byte_stream += bytes([QOI_OP_DIFF | np.uint8(dr + 2) << 4 | np.uint8(dg + 2) << 2 | np.uint8(db + 2)])

                    elif (dg >= -32 and dg <= 31) and ((dr-dg) >= -8 and (dr-dg) <= 7) and ((db-dg) >= -8 and (db-dg) <= 7):
                        byte_stream += bytes([QOI_OP_LUMA | np.uint8(dg + 32), np.uint8(dr-dg + 8) << 4 | np.uint(db-dg + 8)])
                
                    else:
                        byte_stream += bytes([QOI_OP_RGB, r, g, b])

        pr, pg, pb, pa = (r, g, b, a)


    byte_stream += QOI_END_MARKER
    return byte_stream

def decode(path: str) -> Image.Image: # alter later to take in destination file path and save image there.
    with open(path, 'rb') as f:
        qoi_bytes = f.read()
    # later include error handling that checks provided path for qoi extension
    # add exception if qoi file is too big
    header_bytes = qoi_bytes[0:14]
    magic, width, height, channels, colorspace = struct.unpack(FMT_STR, header_bytes)
    if (magic != MAGIC):
        #add more error handling later
        print("error")
    
    im_array = decode_array(height, width, channels, qoi_bytes)
    im_array = np.reshape(im_array, (height, width, channels))
    # (use colorspace here for better formatting?)
    if channels == 3:
        mode = 'RGB'
    else:
        mode = 'RGBA'
    return Image.fromarray(im_array,mode)

def decode_array(height: int, width: int, channels: int, qoi_bytes: bytes) -> np.ndarray:
    index = []
    for _ in range(64):
        index.append((0,0,0,255))
    im_array = np.empty(width * height * channels, dtype='uint8')
    im_offset = 0
    offset =  14
    run_count = 0
    r, g, b, a = (0, 0, 0, 255)
    exit_flag = False
    
    while exit_flag != True:
        current_byte = qoi_bytes[offset]
        if current_byte == QOI_OP_RGBA:
            r, g, b, a = qoi_bytes[offset+1:offset+5]
            offset += 5
        elif current_byte == QOI_OP_RGB:
            r, g, b = qoi_bytes[offset+1:offset+4]
            offset += 4
        else:
            tag = 0xc0 & current_byte
            pr, pg, pb = im_array[im_offset - channels: im_offset - channels + 3]
            if tag == QOI_OP_RUN:
                run_count = (0x3F & current_byte)
                r, g, b = (pr, pg, pb)
                offset += 1        
            elif tag == QOI_OP_INDEX and offset < (len(qoi_bytes)-len(QOI_END_MARKER)):
                hash = 0x3F & current_byte
                r,g,b,a = index[hash]
                offset += 1
            elif tag == QOI_OP_DIFF:
                dr = ((0x30 & current_byte) >> 4) - 2
                dg = ((0x0C & current_byte) >> 2) - 2
                db = (0x03 & current_byte) -2
                r = pr + dr
                g = pg + dg
                b = pb + db
                offset += 1
            elif tag == QOI_OP_LUMA:
                dg = (0x3F & current_byte) - 32
                dr_dg = ((0xF0 & qoi_bytes[offset + 1]) >> 4) - 8
                db_dg = (0x0F & qoi_bytes[offset + 1]) - 8
                dr = dr_dg + dg
                db = db_dg + dg
                r = pr + dr
                g = pg + dg
                b = pb + db
                offset += 2
            else:
                if qoi_bytes[offset:] == QOI_END_MARKER:
                    exit_flag = True
                    if im_offset != (width * height * channels):
                        print("bytes ended before anticipated -- color_stream may have null values at end")
                else:
                    print("uninterpretable byte encountered")
        if exit_flag != True:
            run_count += 1
            for i in range(run_count):
                if channels == 3:
                    im_array[im_offset:im_offset+3] = [r, g, b]
                    im_offset += 3
                else:
                    im_array[im_offset:im_offset+4] = [r, g, b, a]
                    im_offset += 4

            hash = _index_position(r,g,b,a)
            index[hash] = (r,g,b,a)
            run_count = 0
    
    return im_array

# add main function that will serve as a CLI interface.
