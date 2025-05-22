import os
import subprocess
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict
from operator import itemgetter
import argparse

import math
import random

from tqdm import tqdm
import strictyaml as syaml
import requests

vpn_coutries = [
  'Croatia', 
  'Cyprus', 
  'Czech_Republic', 
  'Denmark', 
  'Finland', 
  'France', 
  'Georgia', 
  'Germany', 
  'Ghana', 
  'Greece', 
  'Greenland', 
  'Guam', 
  'Honduras', 
  'Hong_Kong', 
  'Hungary', 
  'Iceland', 
  'India', 
  'Indonesia', 
  'Ireland', 
  'Isle_Of_Man', 
]


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
  data_dir = base_dir / Path('data')
  scores_dir = base_dir / Path('scores')
  
  with open(data_dir / 'scores_w_url.yaml') as f:
    metadata = syaml.load(f.read())
  
  metadata = metadata.data
  
  assert len(metadata.keys()) == len([ v for k, v in metadata.items() if v['imslp_url']]), 'There are scores without IMSLP URL'
  
  cnt = 0
  
  for mscore_id, obj in tqdm(metadata.items()):
    pdf_url, pdf_dir = itemgetter('imslp_url', 'path')(obj)
    pdf_dir = scores_dir / pdf_dir
    pdf_path = pdf_dir / f'sq{mscore_id}.pdf'
    
    if pdf_path.exists():
      continue
    
    res_pdf = requests.get(pdf_url)
    
    with open(pdf_path, 'wb') as pdf_f:
      pdf_f.write(res_pdf.content)
    
    cnt += 1
    
    if cnt % 10 == 0:
      print(f'{cnt} scores downloaded')
      subprocess.call([ 'nordvpn', 'c', vpn_coutries[cnt // 10] ])
    
    time.sleep(3)


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(Path(args.base_dir))