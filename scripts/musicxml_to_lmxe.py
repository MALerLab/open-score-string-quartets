import os
from pathlib import Path
from operator import itemgetter

import math
import random

import json
import csv
import strictyaml as syaml

from tqdm import tqdm
import matplotlib.pyplot as plt

import cv2
import numpy as np

import xml.etree.ElementTree as ET
from modules.lmxe.lmxe import score_to_lmxe

from .utils import get_ts, get_argument_parser


def main(base_dir:Path, log_path):
  data_dir = base_dir / 'data'
  score_dir = base_dir / 'scores'

  with open(data_dir / 'scores_w_infos.yaml') as f:
    metadata = syaml.load(f.read())

  metadata = metadata.data

  score_data = [ 
    dict( sqid=sqid, **obj ) 
    for sqid, obj in metadata.items() 
  ]

  pbar = tqdm(score_data)
  for item in pbar:
    mscore_dir, sqid = itemgetter('path', 'sqid')(item)
    mscore_dir = score_dir / mscore_dir
    
    xml_path = mscore_dir / f'sq{sqid}.musicxml'
    
    pbar.set_description(f'sq{sqid}')
    
    lmxe_dir = mscore_dir / 'lmxe'
    lmxe_dir.mkdir(exist_ok=True)
    
    system_lmxe_dir = lmxe_dir / 'cropped'
    system_lmxe_dir.mkdir(exist_ok=True)
    
    page_lmxe_dir = lmxe_dir / 'original'
    page_lmxe_dir.mkdir(exist_ok=True)
    
    with open(xml_path, 'r') as f:
      xml_str = f.read()
    
    with open(log_path, 'a') as f:
      print('', file=f)
      print(f"----------sq{sqid}----------", file=f)
      
      lmx_score = score_to_lmxe(
        xml_str, 
        error_out=f
      )
    
    for p_i, page in enumerate(lmx_score):
      page_lmxe = []
      
      for s_i, system in enumerate(page):
        system_lmxe = '\n'.join(system)
        system_lmxe_path = system_lmxe_dir / f'sq{sqid}:{str(p_i+1).zfill(4)}:{str(s_i+1).zfill(4)}.lmxe'
        
        with open(system_lmxe_path, 'w') as f:
          f.write(system_lmxe)
        
        page_lmxe.append(system_lmxe)
      
      page_lmxe = '\n\n'.join(page_lmxe)
      page_lmxe_path = page_lmxe_dir / f'sq{sqid}:{str(p_i+1).zfill(4)}.lmxe'
      
      with open(page_lmxe_path, 'w') as f:
        f.write(page_lmxe)


if __name__ == '__main__':
  parser = get_argument_parser([
    ('-d', '--base_dir', True, str),
  ])

  args = parser.parse_args()

  base_dir = Path(args.base_dir)
  log_path = base_dir / f'lmxe_{get_ts()}.log'

  main(base_dir, log_path)