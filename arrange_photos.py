#! /home/andrey/anaconda3/bin/python
import argparse
import os
import pathlib
import shutil
from datetime import datetime
import dateutil.parser
from exifread import process_file
import subprocess


def run(image, target, name=None, config=None):
    with open(image, 'rb') as f:
        pf = process_file(f, stop_tag='DateTimeOriginal', details=False)
        if 'EXIF DateTimeOriginal' in pf:
            date = datetime.strptime(pf['EXIF DateTimeOriginal'].printable, '%Y:%m:%d %H:%M:%S')
        else:
            date = get_mediainfo(image)
        targetDir = os.path.join(target, str(date.year), str(date.month), str(date.day) if name == None else name)
        pathlib.Path(targetDir).mkdir(parents=True, exist_ok=True)
        targetPath = os.path.join(targetDir, os.path.basename(image))
        if os.path.exists(targetPath):
            image_size = os.path.getsize(image)
            target_size = os.path.getsize(targetPath)
            if config['rm'] and image_size == target_size:
                print('REMOVING EXACT COPY (by size): {}'.format(image))
                os.remove(image)
                return
            else:
                raise Exception(
                    "Path already exists!\nold: file://{} ({})\nnew: file://{} ({})\n{}\n".format(image, image_size,
                                                                                                  targetPath,
                                                                                                  target_size,
                                                                                                  'EQUAL' if image_size == target_size else ''))
        print('running {} -> {}'.format(image, targetPath))
        shutil.move(image, targetPath)


def run_dir(input, output, name=None, config=None):
    print("---------------------------------------------")
    print(input)
    print("---------------------------------------------")
    for fn in os.listdir(input):
        try:
            full_fn = os.path.join(input, fn)
            if os.path.isfile(full_fn):
                run(full_fn, output, name, config)
        except Exception as e:
            print(e)
    if not os.listdir(input):
        print("---------------------------------------------")
        print("REMOVING {}".format(input))
        print("---------------------------------------------")
        shutil.rmtree(input)


def get_mediainfo(path):
    output = subprocess.run(["mediainfo", "-f", path], stdout=subprocess.PIPE).stdout.decode()
    date_tags = [i for i in output.split('\n') if ' date' in i]
    tags = {}
    for t in date_tags:
        split = t.split(' :')
        tags[split[0].strip()] = split[1].strip()
    if 'Tagged date' in tags:
        return datetime.strptime(tags['Tagged date'], "UTC %Y-%m-%d %H:%M:%S")
    elif 'File last modification date' in tags:
        return datetime.strptime(tags['File last modification date'], "UTC %Y-%m-%d %H:%M:%S")
    else:
        raise Exception("Didn't find date related tags...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', help='image path')
    parser.add_argument('-d', help='target directory')
    parser.add_argument('-n', help='name of new directory (instead of day)')
    parser.add_argument('-rm', help='remove if exact same size', default=False)

    args = parser.parse_args()
    config = {'rm': args.rm}
    inp = os.path.abspath(args.i)
    outp = os.path.abspath(args.d)
    namep = args.n if args.n else None
    if not os.path.exists(args.i):
        raise Exception("Input path does not exist: {}".format(args.i))
    elif os.path.isdir(args.i):
        run_dir(inp, outp, namep, config)
    else:
        run(inp, outp, namep, config)
