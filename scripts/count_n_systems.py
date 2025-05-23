import argparse
import sys
from pathlib import Path

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


def get_argument_parser():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "-d",
    "--base-dir",
    required=True,
    type=str
  )
  
  return parser


def main(base_dir):
  data_dir = base_dir / 'data'
  score_dir = base_dir / 'scores'
  
  with open(data_dir / 'scores.yaml') as f:
    data = syaml.load(f.read())
  data = data.data
  
  xml_paths = []
  for sqid, body in data.items():
    xml_dir = score_dir / body['path']
    xml_path = xml_dir / f'sq{sqid}.musicxml'
    
    xml_paths.append(xml_path)
  
  print('Number of scores:', len(xml_paths))
  
  for x_p in tqdm(xml_paths):
    with open(x_p, 'r') as f:
      xml = f.read()
    
    xml_tree = ET.ElementTree(ET.fromstring(xml))
    part = xml_tree.getroot().findall('part')[0]
    print_tags = part.findall('.//print')
    
    system_cnt = 1
    systems_in_page = []

    for p_t in print_tags:
      if p_t.get('new-system') == 'yes':
        system_cnt += 1
      
      elif p_t.get('new-page') == 'yes':
        systems_in_page.append(system_cnt)
        system_cnt = 1

    else:
      systems_in_page.append(system_cnt)
    
    data[x_p.stem.replace('sq', '')]['n_pages'] = len(systems_in_page)
    
    if len(systems_in_page) > 0:
      data[x_p.stem.replace('sq', '')]['n_systems'] = systems_in_page
  
  
  with open(data_dir / 'scores_w_infos.yaml', 'w') as f:
    f.write(syaml.as_document(data).as_yaml())


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(Path(args.base_dir))