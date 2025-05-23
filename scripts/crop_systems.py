"""
Crop systems from score page images and pred staff heights using LS-YOLO-Staff model.
1. crop original image according to system bounding box coordinates
2. save cropped images
3. batch inference of LS-YOLO-Staff model using only left half of cropped images
4. save mean height of staffs to staff_heights.csv
"""

import argparse
from pathlib import Path

import math
import random

import json
import csv
import pandas as pd

import cv2

from tqdm.auto import tqdm

from ultralytics import YOLO

from modules.svdp.svdp import bbox_utils
from const import excluded_pages


def get_argument_parser():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "-d",
    "--base-dir",
    required=True,
    type=str
  )
  
  return parser


def load_bboxs(file_path):
  with open(file_path, 'r') as f:
    lines = f.readlines()
  
  bboxs = [ 
    [ int(p) for p in line.strip().split(' ') ] # lx, ly, rx, ry
    for line in lines
  ]

  # sort by y, x
  bboxs = sorted( bboxs, key=lambda x: (x[1], x[0]) )
  
  # merge overlapping bboxs
  bboxs = bbox_utils.merge_match_bboxs(bboxs)

  return bboxs


def main(base_dir:Path):
  score_dir = base_dir / 'scores'

  model_weight_path = base_dir / 'modules' / 'lsyolo' / 'checkpoints' / 'ls-yolo-staff-v2.pt'
  model = YOLO('yolov8m.pt')
  model._load(weights=str(model_weight_path))

  ## crop original image according to system bounding box coordinates
  page_imgs = score_dir.glob('**/images/original/*.png')
  image_bbox_pairs = [ 
    (page_img, page_img.parent / page_img.name.replace('.png', '_systems.txt'))
    for page_img in sorted(page_imgs)
      if page_img.stem not in excluded_pages # filter out excluded pages
  ]
  
  print('# of pages:', len(image_bbox_pairs))

  for i_p, b_p in tqdm(image_bbox_pairs):
    # load image
    img = cv2.imread(i_p, cv2.IMREAD_UNCHANGED)

    # load bboxs
    bboxs = load_bboxs(b_p)

    # make output directory
    o_dir = i_p.parent.parent / 'cropped'
    o_dir.mkdir(exist_ok=True)

    o_imgs = []

    for i, (lx, ly, rx, ry) in enumerate(bboxs):
      # save cropped iamge
      c_i = img[ly:ry, lx:rx]

      c_i_p = o_dir / f'{i_p.stem}_{i}.png'

      cv2.imwrite(c_i_p, c_i)
      o_imgs.append(c_i_p)
    
    # bathch inference
    results = model(o_imgs)

    with open(b_p, 'w') as f:
      for result, (lx, ly, rx, ry) in zip(results, bboxs):
        staff_bboxs = result.boxes.xyxy
        staff_bboxs = staff_bboxs.int().tolist()

        staff_height = [0]

        if len(staff_bboxs) > 0:
          staff_height = [ ry - ly for _, ly, _, ry in staff_bboxs ]
        
        staff_height = sum(staff_height) / len(staff_height)
        staff_height = int(staff_height)
        
        f.write(f'{lx} {ly} {rx} {ry} {staff_height}\n')


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(Path(args.base_dir))