from js import document, console, Uint8Array, File
from pyodide.ffi import create_proxy
import js
import numpy as np
import qoi
import base64
import struct
import asyncio
import io
from PIL import Image, ImageFilter


FMT_STR = '>4sIIBB'
MAGIC = b'qoif'

def add_class(element, class_name):
    element.classList.add(class_name)

async def _handle_selected(e):
    el = document.getElementById('log')
    selected_files = e.target.files
    for file in selected_files:
        type_to = document.getElementById('type-to').value
        tmp = document.createElement('a')
        add_class(tmp, 'listing')
        tmp.id = file.name
        el.appendChild(tmp)
        type_from = _type_checker(file.type, file.name)
        if type_from is None:
            msg = ' | **ERROR: unexpected file type**'
            console.log(msg)
            _log_entry_closeout(file.name, msg)
            return

        tmp.innerHTML = 'NAME: ' + file.name    
        tmp.innerHTML += ' | SIZE: ' + str(file.size)
        tmp.innerHTML += ' | FROM: ' + type_from
        tmp.innerHTML += ' | TO: ' + type_to

        console.log(_strip_name(file.name) + " | " + type_from + " -> " + type_to)
        new_file = await _convert_file(file, type_from, type_to)
        await _download_file(new_file)
        _log_entry_closeout(file.name)

def _log_entry_closeout(filename, msg=''):
    entry = document.getElementById(filename)
    entry.innerHTML += msg + '<br>'
    
def _type_checker(type, name):
    if 'jpg' in type or 'jpeg' in type:
        return "jpeg"
    elif 'png' in type:
        return 'png'
    elif 'qoi' in type:
        return 'qoi'
    elif '.qoi' in name:
        return 'qoi'
    else:
        return None

def _strip_name(filename):
    stripped_name = ''
    exts = ['.jpg','.jpeg','.png','.qoi']
    for ext in exts:
        try:
            stripped_name = (filename)[:(filename).index(ext)]
            return stripped_name
        except:
            continue
    return filename

async def _download_file(file):
    blob = js.Blob.new([file],{type: file.type})
    js.saveAs(blob, file.name)

async def _convert_file(file, type_from, type_to):
    if type_from == type_to:
        return file

    file_name = _strip_name(file.name)
    buf = Uint8Array.new(await file.arrayBuffer())
    bytes = bytearray(buf)

    if type_from == 'png' or type_from == 'jpeg':
        io_bytes = io.BytesIO(bytes)
        im = Image.open(io_bytes)
    
    if type_from == 'jpeg':
        if type_to == 'png':
            stream = io.BytesIO()
            im.save(stream, format='PNG')
            file_name += '.png'
            new_file = File.new([Uint8Array.new(stream.getvalue())], file_name, type='image/png')
        if type_to == 'qoi':
            image_array = np.array(im)
            height, width, channels = image_array.shape
            colorspace = 0 # come back and see if there is a way to get this from the image object
            image_array = np.reshape(image_array, np.size(image_array))
            qoi_array = qoi.encode_array(height, width, channels, colorspace, image_array)
            qoi_stream = io.BytesIO(qoi_array)
            file_name += '.qoi'
            new_file = File.new([Uint8Array.new(qoi_stream.getvalue())], file_name, type='application/octet-stream')

    elif type_from == 'png':
        if type_to == 'jpeg':
            stream = io.BytesIO()
            im.save(stream, format='JPEG')
            new_file = File.new([Uint8Array.new(stream.getvalue())], file.name, type='image/jpeg')
        if type_to == 'qoi':
            image_array = np.array(im)
            height, width, channels = image_array.shape
            colorspace = 0 # come back and see if there is a way to get this from the image object
            image_array = np.reshape(image_array, np.size(image_array))
            qoi_array = qoi.encode_array(height, width, channels, colorspace, image_array)
            qoi_stream = io.BytesIO(qoi_array)
            file_name += '.qoi'
            new_file = File.new([Uint8Array.new(qoi_stream.getvalue())], file_name, type='application/octet-stream')

    elif type_from == 'qoi':
        if type_to == 'jpeg':
            header_bytes = bytes[0:14]
            magic, width, height, channels, colorspace = struct.unpack(FMT_STR, header_bytes)
            if (magic != MAGIC):
                console.log('qoif bytes not found')
            im_array = qoi.decode_array(height, width, channels, bytes)
            im_array = np.reshape(im_array, (height, width, channels)) # can I use colorspace for png or jpeg?
            if channels == 3:
                mode = 'RGB'
            else:
                mode = 'RGBA'
            im_out = Image.fromarray(im_array, mode)
            stream = io.BytesIO()
            im_out.save(stream, 'JPEG')
            file_name += '.jpeg'
            new_file = File.new([Uint8Array.new(stream.getvalue())], file_name, type='image/jpeg')
        if type_to == 'png':
            header_bytes = bytes[0:14]
            magic, width, height, channels, colorspace = struct.unpack(FMT_STR, header_bytes)
            if (magic != MAGIC):
                console.log('qoif bytes not found')
            im_array = qoi.decode_array(height, width, channels, bytes)
            im_array = np.reshape(im_array, (height, width, channels)) # can I use colorspace for png or jpeg?
            if channels == 3:
                mode = 'RGB'
            else:
                mode = 'RGBA'
            im_out = Image.fromarray(im_array, mode)
            stream = io.BytesIO()
            im_out.save(stream, 'PNG')
            file_name += '.png'
            new_file = File.new([Uint8Array.new(stream.getvalue())], file_name, type='image/png')
    
    else:
        console.log ('ERROR - unexpected conversion')
        new_file = File.new([Uint8Array.new('error')], 'error.txt', type='text/plain')

    return new_file
    

handle_selected = create_proxy(_handle_selected)
document.getElementById('file-upload').addEventListener('change', handle_selected)
