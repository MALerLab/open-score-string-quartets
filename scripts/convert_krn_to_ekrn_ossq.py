import warnings
import shutil
import subprocess
from pathlib import Path
import argparse

import math
import random

import json
import csv

from tqdm import tqdm

import cv2
import numpy as np

import kernpy as kp

import xml.etree.ElementTree as ET

from modules.lmxe.lmxe import linearize_lmxe, delinearize_lmxe
from modules.lmxe.lmxe.LMXEFile import LMXEFile, LMXEMetadata
from modules.lmxe.lmxe.vocabulary import *
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.symbolic.part_to_score import parts_to_score 
from modules.lmxe.lmxe.symbolic.Pruner import Pruner

from scripts.utils import get_ts, load_ossq_metadata
from scripts.utils.lmxe_integrity import compare_note_sequences

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')


def main(base_dir:Path, reduced:bool=False):
  prj_root = base_dir
  warning_dump = open('./warning.log', 'w')

  errout = prj_root / f'verify_errors_{get_ts()}.log'
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  data = load_ossq_metadata(data_dir / 'scores_w_infos.yaml')
  pbar = list(data.items())
  pbar = tqdm(pbar)
  
  for score_idx, (sqid, body) in enumerate(pbar):
    mscore_id = f'sq{sqid}'
    
    xml_dir = score_dir / body['path']
    krn_dir = xml_dir / 'krn'
    
    kern_paths = sorted( krn_dir.glob('*.krn') )

    for k_p in tqdm(kern_paths, leave=False, desc=f"{mscore_id}"):
      try:
        doc, _ = kp.load(k_p)
        kp.dump(
          doc,
          k_p.with_suffix('.ekrn'),
          encoding=kp.Encoding.eKern
        )
        
        with open(errout, 'a') as errout_f:
          print(f"[OK] : {k_p.name}", file=errout_f)
      
      except Exception as e:
        with open(errout, 'a') as errout_f:
          print(f"[ER] : {k_p.name} : {e}", file=errout_f)
  
  warning_dump.close()


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument(
    '-d', '--base_dir', 
    required=True, 
    type=str
  )
  parser.add_argument(
    '-r', '--reduced',
    required=False,
    choices=[1, 0],
    default=0,
    type=int
  )
  
  args = parser.parse_args()

  main(Path(args.base_dir), reduced=bool(args.reduced))