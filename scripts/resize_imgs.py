"""
Image resizing based on inferenced staff heights
"""

import os
from pathlib import Path
import shutil
from datetime import datetime

import math
import random

import json
import csv

import cv2

from tqdm.auto import tqdm

from .const import excluded_pages
from .utils import get_argument_parser, load_bboxs


def main(base_dir:Path, target_height:int):
  score_dir = base_dir / 'scores'

  bbox_paths = score_dir.glob('**/images/synthetic/original/*_system_bboxs.txt')
  bbox_paths = [ 
    p
    for p in sorted(bbox_paths)
      if p.stem.replace('_system_bboxs', '') not in excluded_pages 
      # filter out excluded pages
  ]

  print('# of pages:', len(bbox_paths))

  for b_p in tqdm(bbox_paths):
    # load bboxs
    bboxs = load_bboxs(b_p, merge=False)

    for i, (*_, staff_height) in enumerate(bboxs):
      # load image
      i_p = b_p.parent.parent / 'cropped' / b_p.name.replace('_system_bboxs.txt', f':{str(i+1).zfill(4)}.png')
      img = cv2.imread(i_p, cv2.IMREAD_UNCHANGED)

      h, w = img.shape[:2]
      ratio = target_height / staff_height

      i_r = cv2.resize(img, (int(w * ratio), int(h * ratio)), interpolation=cv2.INTER_AREA)
      i_r = cv2.cvtColor(i_r, cv2.COLOR_RGB2GRAY)

      # Save the resized image
      out_dir = i_p.parent.parent / 'crop_resized'
      out_dir.mkdir(exist_ok=True)

      cv2.imwrite(out_dir / i_p.name, i_r)


if __name__ == '__main__':
  parser = get_argument_parser([
    ('-d', '--base_dir', True, str),
    ('-t', '--target_height', True, int),
  ])

  args = parser.parse_args()

  base_dir = Path(args.base_dir)
  target_height = args.target_height

  main(base_dir, target_height)