import os
import sys
import subprocess
import warnings
from typing import Union, Any, Optional
import shutil
from pathlib import Path
from collections import Counter, defaultdict
from operator import itemgetter
from itertools import groupby
from tempfile import NamedTemporaryFile, TemporaryDirectory

import math
import random

import json
import csv
import strictyaml as syaml

from tqdm import tqdm
import matplotlib.pyplot as plt

import cv2
import numpy as np
import partitura as pt

import xml.etree.ElementTree as ET
from lmx_utils import score_to_lmxe


root_dir = Path(os.getcwd())
data_dir = root_dir / 'data'
score_dir = root_dir / 'scores'

with open(data_dir / 'scores.yaml') as f:
  score_metadata = syaml.load(f.read())

score_metadata = score_metadata.data

mscore_data = [ dict( mscore_id=mscore_id, **obj ) for mscore_id, obj in score_metadata.items() ]

score_pbar = tqdm(mscore_data)
for item in score_pbar:
  sub_dir, mscore_id = itemgetter('path', 'mscore_id')(item)
  xml_path = score_dir / sub_dir / f'sq{mscore_id}.musicxml'
  
  score_pbar.set_description(f'sq{mscore_id}')
  
  lmxe_dir = score_dir / sub_dir / 'lmxe'
  lmxe_dir.mkdir(exist_ok=True)
  
  if len( list(lmxe_dir.glob('*.lmxe')) ) == len( list((score_dir/sub_dir/'images'/'original').glob('*.png')) ):
    continue
  
  with open(xml_path, 'r') as f:
    xml_str = f.read()
  
  with open('./error.log', 'w') as f:
    lmx_score = score_to_lmxe(
      xml_str, 
      error_out=f
    )
  
  for p_i, page in enumerate(lmx_score):
    lmxe_str = '\n\n'.join([ '\n'.join(system)  for system in lmx_score[0] ])
    lmxe_path = lmxe_dir / f'sq{mscore_id}:{str(p_i+1).zfill(4)}.lmxe'
    
    with open(lmxe_path, 'w') as f:
      f.write(lmxe_str)