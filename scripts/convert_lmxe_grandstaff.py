import warnings
import shutil
from pathlib import Path
import argparse

import math
import random

import json
import csv

from tqdm import tqdm

import cv2
import numpy as np

import xml.etree.ElementTree as ET

from modules.lmxe.lmxe import linearize_lmxe, delinearize_lmxe
from modules.lmxe.lmxe.Delinearizer import inject_times_to_reduced_lmxe
from modules.lmxe.lmxe.LMXEFile import LMXEFile, LMXEMetadata
from modules.lmxe.lmxe.vocabulary import *
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.symbolic.part_to_score import parts_to_score 
from modules.lmxe.lmxe.symbolic.Pruner import Pruner

from scripts.utils import get_ts, get_argument_parser, load_ossq_metadata
from scripts.utils.lmxe_integrity import compare_note_sequences, remove_consecutive_items

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')

def main(
  base_dir:Path,
  reduced:bool=False, 
  verify:bool=True
):
  warning_dump = open('./warning.log', 'w') # dummpy log file to suppress warnings from lmxe module
  errout = base_dir / f'verify_errors_grandol_{get_ts()}.log'

  with open(base_dir / 'full-segments.csv', 'r') as f:
    data = csv.reader(f)
    header = next(data)
    data = list(data)

  assert all([ 
    (base_dir / composer / collection / piece / f'{segment}.musicxml').exists()
    for composer, collection, piece, segment, *_ in data
  ]), "Some MusicXML files listed in 'full-segments.csv' do not exist."

  pbar = tqdm(data)
  for score_idx, r in enumerate(pbar):
    composer, collection, piece, segment, *_ = r

    xml_path = base_dir / composer / collection / piece / f'{segment}.musicxml'

    ext_name = '.lmxe' if not reduced else '.rlmxe'    
    lmxe_path = base_dir / composer / collection / piece / f'{segment}{ext_name}'
    
    lmxe_score_type, lmxe_score = linearize_lmxe(
      xml=xml_path,
      reduced=reduced,
      error_out=warning_dump,
      fail_on_unknown_tokens=True
    )
    
    # save LMXE files per system
    for p_idx, page in enumerate(lmxe_score):
      for s_idx, system in enumerate(page):
        number_of_parts, measure_nos, times, system = system
        number_of_measures = len(system)

        metadata = LMXEMetadata(
          score_type=lmxe_score_type,
          dataset='grandstaff-lmx',
          score_id=f'{composer}/{collection}/{piece}',
          page_idx=p_idx + 1,
          system_idx=s_idx + 1,
          number_of_parts=number_of_parts,
          measure_start=measure_nos[0],
          measure_end=measure_nos[-1],
          number_of_measures=number_of_measures,
          measure_numbers=measure_nos,
          times=times,
        )

        LMXEFile.write(lmxe_path, '\n'.join(system), metadata)
    
    if not verify:
      return

    full_score_lmxe = LMXEFile.load(lmxe_path)
    
    if reduced:
      full_score_lmxe.measures = inject_times_to_reduced_lmxe(
        full_score_lmxe.measures,
        full_score_lmxe.metadata.times
      )

    delin_xml_path = base_dir / composer / collection / piece / f'{segment}.delin'
    delin_full_score = delinearize_lmxe(full_score_lmxe)
    delin_full_score.write(delin_xml_path)
    
    pruner = Pruner()
    full_score_musicxml = MusicXMLFile.load_musicxml(xml_path)
    part = full_score_musicxml.tree.getroot().find('part')
    pruner.process_part(part)

    pruned_xml_path = base_dir / composer / collection / piece / f'{segment}.pruned'
    pruned_xml = MusicXMLFile(parts_to_score([('grandstaff', part)]))
    pruned_xml.write(pruned_xml_path)
    
    with open(errout, 'a') as errout_f:
      score_id = f'{composer}/{collection}/{piece}/{segment}'
      try:
        are_same, msg = compare_note_sequences(xml_path, delin_xml_path, tolerance=0.02)
        if not are_same:
          print(f"[ER]: {score_id}: {msg}", file=errout_f)
        else:
          print(f"[OK]: {score_id}: {msg}", file=errout_f)
      except:
        print(f"[EX]: {score_id}: Exception occurred during comparison", file=errout_f)
      
      # print('', file=errout_f)


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
  parser.add_argument(
    '-v', '--verify',
    required=False,
    choices=[1, 0],
    default=1,
    type=int
  )
  
  
  args = parser.parse_args()

  main(Path(args.base_dir), reduced=bool(args.reduced), verify=bool(args.verify))