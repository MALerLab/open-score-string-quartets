import sys
sys.path.append('/home/dongmin/userdata/latent_score_dataset')

import os
from datetime import datetime
from pathlib import Path
import argparse
from typing import Union, List

import csv
import json
import strictyaml as syaml

from tqdm import tqdm

import numpy as np
import cv2

import bbox_utils
import bootleg_utils
from flatten_utils import process_image, flatten_images


get_ts = lambda: datetime.now().strftime('%Y-%m-%d-%H:%M:%S')


def flatten_scores(tgt_list, metadata_writer, error_log_path):
  for tgt in tqdm(tgt_list):
    image_dir = tgt.parent.parent # '/.../composer/title/images'
    output_dir = image_dir / 'flattened'
    
    try:
      if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
      
      out_path = output_dir / tgt.name
      
      crop_bboxs, staff_group_pos, img, hlines, vlines = process_image(tgt, error_log_path)
      
      crop_bboxs, staff_group_pos = bootleg_utils.filter_faded_area(img, crop_bboxs, staff_group_pos, window_length=5)
      
      num_staves = len(crop_bboxs)
      
      i_flt = flatten_images(crop_bboxs, staff_group_pos, img, hlines, vlines, include_notes=False, error_log_cfg=(error_log_path, tgt))
      
      cv2.imwrite( out_path, i_flt )
      
      metadata_writer.writerow([*tgt.stem.split(':'), i_flt.shape[1], i_flt.shape[0], num_staves])
      
    except Exception as e:
      with open(error_log_path, 'a') as error_:
        print( ','.join(tgt.stem.split(':')), e, sep=',', file=error_ )


if __name__ == '__main__':
  root_dir = Path(os.getcwd())
  data_dir = root_dir / 'data'
  score_dir = root_dir / 'scores'
  
  with open(data_dir / 'scores.yaml') as f:
    score_metadata = syaml.load(f.read())
  
  score_metadata = score_metadata.data
  
  tgt_list = [
    path
    for mscore_id, infos in score_metadata.items()
    for path in list(sorted((score_dir / infos['path'] / 'images' / 'original').glob('*.png')))
  ]
  
  error_log_path = root_dir / f'flatten_error_{get_ts()}.log'
  if not error_log_path.exists():
    error_log_path.touch()
  
  with open(data_dir / f'flattened_metadata_{get_ts()}.csv', 'w') as metadata_f:
    writer = csv.writer(metadata_f)
    writer.writerow(['mscore_id', 'page_index', 'width', 'height', 'num_staves'])
    flatten_scores(tgt_list, writer, error_log_path)
  
  # python3 flatten_scores.py "string_quartet"