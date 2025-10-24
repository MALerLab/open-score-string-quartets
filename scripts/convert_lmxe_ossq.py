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


def main(base_dir:Path, reduced:bool=False, verify:bool=True):
  prj_root = base_dir

  errout = prj_root / f'verify_errors_{get_ts()}.log'
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  data = load_ossq_metadata(data_dir / 'scores_w_infos.yaml')
  pbar = list(data.items())
  pbar = tqdm(pbar)
  for score_idx, (sqid, body) in enumerate(pbar):
    # if score_idx not in {32, 70, 95, 113}:
    # continue

    mscore_id = f'sq{sqid}'
    if mscore_id not in ['sq7295726']:
      continue
    pbar.set_description(mscore_id)

    xml_dir = score_dir / body['path']
    xml_path = xml_dir / f'{mscore_id}_cleaned.musicxml'
    
    temp_dir = xml_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    lmxe_dir = xml_dir / 'lmxe'
    lmxe_dir.mkdir(exist_ok=True)
    
    lmxe_score_type, lmxe_score = linearize_lmxe(
      xml=xml_path,
      reduced=reduced
    )
    
    ext_name = '.lmxe' if not reduced else '.rlmxe'    
    # save LMXE files per system
    for p_idx, page in enumerate(lmxe_score):
      for s_idx, system in enumerate(page):
        number_of_parts, measure_nos, times, system = system
        number_of_measures = len(system)

        metadata = LMXEMetadata(
          score_type=lmxe_score_type,
          dataset='open-score-string-quartets',
          score_id=mscore_id,
          page_idx=p_idx + 1,
          system_idx=s_idx + 1,
          number_of_parts=number_of_parts,
          measure_start=measure_nos[0],
          measure_end=measure_nos[-1],
          number_of_measures=number_of_measures,
          measure_numbers=measure_nos,
          times=times,
        )

        lmxe_path = lmxe_dir / f'{mscore_id}:{str(p_idx+1).zfill(4)}:{str(s_idx+1).zfill(4)}{ext_name}'

        LMXEFile.write(lmxe_path, '\n'.join(system), metadata)
    
    if not verify:
      return

    lmxe_paths = list(sorted(lmxe_dir.glob(f'{mscore_id}:*{ext_name}')))

    number_of_parts = LMXEFile.load(lmxe_paths[0]).metadata.number_of_parts
    full_metadata = LMXEMetadata(
      score_type=lmxe_score_type,
      dataset='open-score-string-quartets',
      score_id=mscore_id,
      page_idx=-1,
      system_idx=-1,
      measure_start=measure_nos[0],
      number_of_parts=number_of_parts,
      measure_end=measure_nos[-1],
      measure_numbers=[],
      times=[],
    )
    full_score = []

    for l_p in lmxe_paths:
      l = LMXEFile.load(l_p)
      system = l.measures
      full_score.extend(system)
      
      full_metadata.measure_numbers.extend(l.metadata.measure_numbers)
      full_metadata.times.extend(l.metadata.times)
    
    full_metadata.measure_start = full_metadata.measure_numbers[0]
    full_metadata.measure_end = full_metadata.measure_numbers[-1]

    full_score_lmxe_path = temp_dir / f'{mscore_id}_full{ext_name}'
    LMXEFile.write(full_score_lmxe_path, '\n'.join(full_score), full_metadata)
    
    if reduced:
      full_score_lmxe_path = LMXEFile.load(full_score_lmxe_path)
      full_score_lmxe_path.measures = inject_times_to_reduced_lmxe(
        full_score_lmxe_path.measures,
        full_metadata.times
      )

    delin_full_score_musicxml = delinearize_lmxe(full_score_lmxe_path)

    delin_part_musicxml_paths = []
    for p_idx, part in enumerate(delin_full_score_musicxml.tree.getroot().findall('part')):
      part_musicxml_path = temp_dir / f'{mscore_id}_delin_{part.get("id")}.musicxml'
      part_musicxml = MusicXMLFile(parts_to_score(
        [('multi', part)], 
        measure_numbers=full_metadata.measure_numbers
      ))
      part_musicxml.write(part_musicxml_path)

      delin_part_musicxml_paths.append(part_musicxml_path)
    
    pruner = Pruner()
    full_score_musicxml = MusicXMLFile.load_musicxml(xml_path)
    part_musicxml_paths = []
    for part in full_score_musicxml.tree.getroot().findall('part'):
      pruner.process_part(part)
      part_musicxml_path = temp_dir / f'{mscore_id}_{part.get("id")}.musicxml'
      part_musicxml = MusicXMLFile(parts_to_score([('multi', part)]))
      part_musicxml.write(part_musicxml_path)
      part_musicxml_paths.append(part_musicxml_path)
    
    with open(errout, 'a') as errout_f:
      print(f'------ {mscore_id} ------', file=errout_f)
      for i, (orig, delin) in enumerate(zip(part_musicxml_paths, delin_part_musicxml_paths)):
        try:
          are_same, msg = compare_note_sequences(orig, delin, tolerance=0.02)
          if not are_same:
            print(f"[ERROR] {mscore_id}: part {i+1}: {msg}", file=errout_f)
          else:
            print(f"[OK] {mscore_id}: part {i+1}: {msg}", file=errout_f)
        except:
          print(f"[ERROR] {mscore_id}: part {i+1}: Exception occurred during comparison", file=errout_f)
      
      print('', file=errout_f)


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