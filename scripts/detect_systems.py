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

from utils import get_argument_parser


def main(base_dir:Path):
  score_dir = base_dir / 'scores'
  
  # model_weight_path = base_dir / 'modules' / 'lsyolo' / 'checkpoints' / 'ls-yolo-system.pt'
  model_weight_path = base_dir / 'modules' / 'lsyolo' / 'checkpoints' / 'ls-yolo-system-v2.pt'
  
  model = YOLO('yolov8m.pt')
  model._load(weights=str(model_weight_path))
  
  page_imgs = score_dir.glob('**/images/original/*.png')
  page_imgs = list(sorted(page_imgs))
  
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
      o_path = orig_path.parent / f'{orig_fn}_systems.txt'
      
      with open( o_path, 'w') as f:
        for lx, ly, rx, ry in bboxs:
          f.write(f'{lx} {ly} {rx} {ry}\n')


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(Path(args.base_dir))