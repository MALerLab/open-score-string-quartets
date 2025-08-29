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

import xml.etree.ElementTree as ET

import json
import cv2

from tqdm.auto import tqdm

from modules.lsyolo import bbox_utils 


get_ts = lambda: datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
dformat = lambda d: json.dumps(d, indent=2)
dprint = lambda d: print(dformat(d))

PathLike = Union[Path, str]


def get_argument_parser(args=None):
  parser = argparse.ArgumentParser()

  if args is None:
    args = [
      ('-d', '--base_dir', True, str),
    ]

  for short, full, required, type_ in args:
    parser.add_argument(
      short,
      full,
      required=required,
      type=type_
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



# <-------------------- Deprecated -------------------->
class deprecated():
  def delete_old_musicxml_files(metadata, score_dir):
    """
    Delete all MusicXML files in the data directory.
    """
    for ossq_id, infos in metadata.items():
      ossq_id = f'sq{ossq_id}'
      
      mscore_dir = score_dir / infos['path'] 
      musicxml_path = mscore_dir / f"{ossq_id}.musicxml"
      
      image_paths = (mscore_dir / 'images' / 'original').glob('*.png')
      image_paths = list(sorted(image_paths))
      
      assert musicxml_path.exists(), f"old score: {str(musicxml_path)} does not exist"
      assert all([ p.exists() for p in image_paths ]), f"old score: some images do not exist"
      
      # delete old files
      musicxml_path.unlink()
      for p in image_paths:
        p.unlink()


  def merge_external_files(metadata, score_dir, out_dir):
    score_pbar = tqdm(metadata.items())
    
    for ossq_id, infos in score_pbar:
      ossq_id = f'sq{ossq_id}'
      
      score_pbar.set_description(f"{ossq_id}")
      
      new_mscore_dir = out_dir / infos['path']
      new_musicxml_path = new_mscore_dir / f'{ossq_id}.musicxml'
      new_image_paths = (new_mscore_dir / 'images' / 'original').glob('*.png')
      new_image_paths = list(sorted(new_image_paths))
      
      assert new_musicxml_path.exists(), f"{str(new_musicxml_path)} does not exist"
      assert all([ p.exists() for p in new_image_paths ]), f"some images do not exist"
      
      mscore_dir = score_dir / infos['path'] 
      musicxml_path = mscore_dir / f"{ossq_id}.musicxml"
      image_dir = mscore_dir / 'images' / 'original'
      
      # copy new files
      shutil.copy(new_musicxml_path, musicxml_path)
      for src_img in new_image_paths:
        shutil.copy(src_img, image_dir / src_img.name)


  def delete_old_lmxe(metadata, score_dir):
    score_pbar = tqdm(metadata.items())
    for mscore_id, infos in score_pbar:
      ossq_id = f'sq{mscore_id}'
      score_pbar.set_description(f"{ossq_id}")
      
      mscore_dir = score_dir / infos['path'] 
      lmxe_paths = (mscore_dir / 'lmxe').glob('*.lmxe')
      
      for p in lmxe_paths:
        p.unlink()