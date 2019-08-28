# Copyright (c) 2019  PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time
import shutil
import requests
import sys
import tarfile
import zipfile
import platform

lasttime = time.time()
FLUSH_INTERVAL = 0.1

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
PDSEG_PATH = os.path.join(LOCAL_PATH, "..", "pdseg")


def get_platform():
    return platform.platform()


def is_windows():
    return get_platform().lower().startswith("windows")


def progress(str, end=False):
    global lasttime
    if end:
        str += "\n"
        lasttime = 0
    if time.time() - lasttime >= FLUSH_INTERVAL:
        sys.stdout.write("\r%s" % str)
        lasttime = time.time()
        sys.stdout.flush()


def _download_file(url, savepath, print_progress):
    r = requests.get(url, stream=True)
    total_length = r.headers.get('content-length')

    if total_length is None:
        with open(savepath, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    else:
        with open(savepath, 'wb') as f:
            dl = 0
            total_length = int(total_length)
            starttime = time.time()
            if print_progress:
                print("Downloading %s" % os.path.basename(savepath))
            for data in r.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)
                if print_progress:
                    done = int(50 * dl / total_length)
                    progress("[%-50s] %.2f%%" %
                             ('=' * done, float(dl / total_length * 100)))
        if print_progress:
            progress("[%-50s] %.2f%%" % ('=' * 50, 100), end=True)


def _uncompress_file(filepath, extrapath, delete_file, print_progress):
    if print_progress:
        print("Uncompress %s" % os.path.basename(filepath))

    if filepath.endswith("zip"):
        handler = _uncompress_file_zip
    else:
        handler = _uncompress_file_tar

    for total_num, index in handler(filepath, extrapath):
        if print_progress:
            done = int(50 * float(index) / total_num)
            progress(
                "[%-50s] %.2f%%" % ('=' * done, float(index / total_num * 100)))
    if print_progress:
        progress("[%-50s] %.2f%%" % ('=' * 50, 100), end=True)

    if delete_file:
        os.remove(filepath)


def _uncompress_file_zip(filepath, extrapath):
    files = zipfile.ZipFile(filepath, 'r')
    filelist = files.namelist()
    total_num = len(filelist)
    for index, file in enumerate(filelist):
        files.extract(file, extrapath)
        yield total_num, index
    files.close()
    yield total_num, index


def _uncompress_file_tar(filepath, extrapath):
    files = tarfile.open(filepath, "r:gz")
    filelist = files.getnames()
    total_num = len(filelist)
    for index, file in enumerate(filelist):
        files.extract(file, extrapath)
        yield total_num, index
    files.close()
    yield total_num, index


def download_file_and_uncompress(url,
                                 savepath=None,
                                 extrapath=None,
                                 print_progress=True,
                                 cover=False,
                                 delete_file=True):
    if savepath is None:
        savepath = "."

    if extrapath is None:
        extrapath = "."

    savename = url.split("/")[-1]
    savepath = os.path.join(savepath, savename)
    extraname = ".".join(savename.split(".")[:-1])
    extraname = os.path.join(extrapath, extraname)

    if cover:
        if os.path.exists(savepath):
            shutil.rmtree(savepath)
        if os.path.exists(extraname):
            shutil.rmtree(extraname)

    if not os.path.exists(extraname):
        if not os.path.exists(savepath):
            _download_file(url, savepath, print_progress)
        _uncompress_file(savepath, extrapath, delete_file, print_progress)


def _pdseg(command, flags, options, devices):
    script = "{}{}{}.py".format(PDSEG_PATH, os.sep, command)
    flags = " ".join(flags)
    options = " ".join(options)
    if is_windows():
        set_cuda_command = "set CUDA_VISIBLE_DEVICES={}".format(
            ",".join(devices))
    else:
        set_cuda_command = "export CUDA_VISIBLE_DEVICES={}".format(
            ",".join(devices))
    cmd = "{} && python {} {} {}".format(set_cuda_command, script, flags,
                                         options)
    print(cmd)
    os.system(cmd)


def train(flags, options, devices):
    _pdseg("train", flags, options, devices)


def eval(flags, options, devices):
    _pdseg("eval", flags, options, devices)


def vis(flags, options, devices):
    _pdseg("vis", flags, options, devices)


def export_model(flags, options, devices):
    _pdseg("export_model", flags, options, devices)