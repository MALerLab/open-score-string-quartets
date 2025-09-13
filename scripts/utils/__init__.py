import os
from datetime import datetime
import operator
import time
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Union, Any, Optional
from tempfile import NamedTemporaryFile, TemporaryDirectory
from itertools import groupby

import xml
import xml.etree.ElementTree as ET

import json
import strictyaml as syaml

from tqdm.auto import tqdm

import cv2
import music21

from modules.lsyolo import bbox_utils 


get_ts = lambda: datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
dformat = lambda d: json.dumps(d, indent=2)
dprint = lambda d: print(dformat(d))

PathLike = Union[Path, str]


def load_ossq_metadata(path:PathLike) -> dict[str,Any]:
  if isinstance(path, str):
    path = Path(path)
  
  assert path.exists(), "Metadata file not found"
  assert path.suffix in [ '.yaml', '.yml' ], "Only YAML file expected"

  with open(path, 'r') as f:
    data = syaml.load(f.read()).data
  
  metadata = {
    str(k): dict(
      sqid=f'sq{k}',
      xml_path=v['path']+f'/sq{k}.musicxml',
      **v
    )
    for k, v in data.items()
  }
  
  return metadata


def get_argument_parser(args=None):
  parser = argparse.ArgumentParser()

  if args is None:
    args = [
      ('-d', '--base_dir', True, str),
    ]

  for short, full, required, _type in args:
    parser.add_argument(
      short,
      full,
      required=required,
      type=_type
    )
  
  return parser


def merge_yolo_bboxs(bboxs, min_ratio=0.2):
  if len(bboxs) < 2:
    return bboxs
  
  prev = 0
  for _ in range(100):
    bboxs = sorted( bboxs, key=lambda x: bbox_utils.get_box_area(x), reverse=True )
    bboxs = bbox_utils.merge_match_bboxs(bboxs, min_ratio=min_ratio)
    
    if len(bboxs) == prev:
      break
    
    prev = len(bboxs)
  
  # sort by y, x
  bboxs = sorted( bboxs, key=lambda x: (x[1], x[0]) )
  
  return bboxs


def load_bboxs(file_path, merge=True, min_ratio=0.2):
  with open(file_path, 'r') as f:
    lines = f.readlines()
  
  bboxs = [ 
    [ int(p) for p in line.strip().split(' ') ] # lx, ly, rx, ry, (height)
    for line in lines
  ]

  if not merge:
    bboxs = sorted( bboxs, key=lambda x: (x[1], x[0]) )
    return bboxs

  # merge overlapping bboxs
  bboxs = merge_yolo_bboxs(bboxs, min_ratio=min_ratio)
  
  return bboxs


def spawn_processes(process_configs, env):
  processes = []
  for config in process_configs:
    process = subprocess.Popen(config, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes.append(process)
    time.sleep(2)  # give process time to start
  
  return processes


def terminate_processes(processes):
  for p in processes:
    try:
      p.terminate()
      p.wait(timeout=5)
    except subprocess.TimeoutExpired:
      p.kill()
      p.wait()


def strip_musicXML(xml: str) -> str:
  """
  remove all <print new-system="yes"/>
  using etree
  """
  root = ET.fromstring(xml)

  for measure in root.findall('.//measure'):
    print_els = measure.findall('.//print[@new-system="yes"]')
    for el in print_els:
      measure.remove(el)

  return ET.tostring(root, encoding="unicode")


def search_letter_box_by_axis(img, nrange, axis, ratio, margin, default=None, compare_fn=operator.gt):
  line_size = img.shape[1-axis]
  nrange = list(nrange)
  
  for i in nrange:
    slice_tup = tuple( i if d == axis else slice(None) for d in range(2) )
    line = img[slice_tup]
    
    # default: (line.sum() / line_size) > ratio
    if compare_fn(line.sum() / line_size, ratio):
      return i + margin
  
  return default if default is not None else nrange[0]


def crop_white_space(img, margin=10, ratio=0.5, compare_fn=operator.gt):
  h, w = img.shape[:2]

  i_g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
  _, ith = cv2.threshold(i_g, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
  
  inrm = 1 - (ith / 255)

  # scan through y axis until meet some non-black things
  yaxis = range(h)
  yst = search_letter_box_by_axis(inrm, yaxis, 0, ratio, -margin, compare_fn=compare_fn)
  yed = search_letter_box_by_axis(inrm, reversed(yaxis), 0, ratio, margin, compare_fn=compare_fn)
  yst = max(0, yst)
  yed = min(h, yed)
  
  # scan through x axis until meet some non-black things
  xaxis = range(w)
  xst = search_letter_box_by_axis(inrm, xaxis, 1, ratio, -margin, compare_fn=compare_fn)
  xed = search_letter_box_by_axis(inrm, reversed(xaxis), 1, ratio, margin, compare_fn=compare_fn)
  xst = max(0, xst)
  xed = min(w, xed)
  
  return img[yst:yed, xst:xed]