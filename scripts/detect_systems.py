import os
from pathlib import Path
import shutil
from collections import Counter

import math
import random

import json
import csv
import pandas as pd

import argparse
import cv2

import matplotlib.pyplot as plt
from tqdm.auto import tqdm

from ultralytics import YOLO

from scripts.utils import get_argument_parser


def main(base_dir:Path, pdf_type:str='scanned'):
  score_dir = base_dir / 'scores'
  
  model_weight_path = base_dir / 'modules' / 'lsyolo' / 'checkpoints' / 'ls-yolo-system-v3.0.0.pt'
  
  model = YOLO('yolov8m.pt')
  model._load(weights=str(model_weight_path))
  
  page_imgs = score_dir.glob(f'**/images/{pdf_type}/original/*.png')
  page_imgs = sorted(page_imgs)
  
  if pdf_type == 'scanned':
    page_alignments = {}
    for p in sorted(score_dir.glob(f'**/sq*_scanned.csv')):
      with open(p, 'r') as f:
        r = f.readlines()[0].rstrip().split(':')
        page_alignments[p.stem.split('_')[0]] = r
    
    page_imgs_filtered = []
    for p in page_imgs:
      sq_id, p_idx = p.stem.split(':')
      
      # if sq_id != 'sq10517302':
      #   continue
      
      p_idx = int(p_idx)
      
      st, ed = page_alignments[sq_id]
      st = int(st) if st != '' else 0 # convert empty to 0, p_idx starts from 1
      ed = int(ed) if ed != '' else 1_000_000 # just a large number for no limit
      
      in_range = st <= p_idx <= ed
      
      if in_range:
        page_imgs_filtered.append(p)
    
    page_imgs = page_imgs_filtered
    del page_imgs_filtered
  
  print('# of segments:', len(page_imgs))
  
  # batch inference
  batch_size = 24
  num_batches = math.ceil( len(page_imgs) / batch_size )

  for cur_batch_idx in tqdm(range(num_batches)):
    batch = page_imgs[cur_batch_idx*batch_size:(cur_batch_idx+1)*batch_size]
    results = model(batch)

    for result in results:
      orig_path = Path(result.path)
      orig_fn = orig_path.stem
      bboxs = result.boxes.xyxy
      bboxs = bboxs.int().tolist()

      # skip if no bbox
      if len(bboxs) < 1:
        continue

      # sort by y, x
      bboxs = sorted( bboxs, key=lambda x: (x[1], x[0]) )

      # save bboxs
      o_path = orig_path.parent / f'{orig_fn}_yolo_bboxs.txt'
      
      with open( o_path, 'w') as f:
        for lx, ly, rx, ry in bboxs:
          f.write(f'{lx} {ly} {rx} {ry}\n')


if __name__ == '__main__':
  parser = get_argument_parser()
  parser.add_argument(
    '-t', '--pdf-type',
    required=True,
    type=str,
    default='scanned',
    choices=['scanned', 'synthetic']
  )
  
  args = parser.parse_args()
  
  main(Path(args.base_dir), args.pdf_type)