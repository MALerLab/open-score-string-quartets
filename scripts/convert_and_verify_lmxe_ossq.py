import warnings
import shutil
from pathlib import Path

import math
import random

import json
import csv

from tqdm import tqdm

import cv2
import numpy as np

import xml.etree.ElementTree as ET

from modules.lmxe.lmxe import linearize_lmxe, delinearize_lmxe
from modules.lmxe.lmxe.LMXEFile import LMXEFile, LMXEMetadata
from modules.lmxe.lmxe.vocabulary import *
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.symbolic.part_to_score import parts_to_score 

from scripts.utils import get_ts, get_argument_parser, load_ossq_metadata
from scripts.utils.lmxe_integrity import compare_note_sequences

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')


def main(base_dir:Path):
  prj_root = base_dir

  errout = prj_root / f'verify_errors_{get_ts()}.log'
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  data = load_ossq_metadata(data_dir / 'scores_w_infos.yaml')
  # data = {k: v for k, v in data.items() if k in ['7093885', '7070781', '7078259', '7075297'] }
  pbar = list(data.items())
  pbar = tqdm(pbar)
  for score_idx, (sqid, body) in enumerate(pbar):
    # if score_idx not in {3, 4, 23, 25, 28, 31, 32, 36, 47, 62, 67, 69, 70, 95, 101, 103, 104, 113, 115, 120}:
    #   continue

    mscore_id = f'sq{sqid}'
    pbar.set_description(mscore_id)

    xml_dir = score_dir / body['path']
    xml_path = score_dir / body['xml_path']
    
    temp_dir = xml_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    lmxe_dir = xml_dir / 'lmxe'
    lmxe_dir.mkdir(exist_ok=True)
    
    lmxe_score_type, lmxe_score = linearize_lmxe(xml=xml_path)
    
    # save LMXE files per system
    for p_idx, page in enumerate(lmxe_score):
      for s_idx, system in enumerate(page):
        measure_nos, system = system

        metadata = LMXEMetadata(
          score_type=lmxe_score_type,
          dataset='open-score-string-quartets',
          score_id=mscore_id,
          page_idx=p_idx + 1,
          system_idx=s_idx + 1,
          measure_start=measure_nos[0],
          measure_end=measure_nos[-1],
          measure_numbers=measure_nos,
          number_of_parts=system[0].count('part:')
        )

        lmxe_path = lmxe_dir / f'{mscore_id}:{str(p_idx+1).zfill(4)}:{str(s_idx+1).zfill(4)}.lmxe'

        LMXEFile.write(lmxe_path, '\n'.join(system), metadata)

    lmxe_paths = list(sorted(lmxe_dir.glob(f'{mscore_id}:*.lmxe')))

    number_of_parts = LMXEFile.load(lmxe_paths[0]).metadata.number_of_parts
    full_metadata = LMXEMetadata(
      score_type=lmxe_score_type,
      dataset='open-score-string-quartets',
      score_id=mscore_id,
      page_idx=-1,
      system_idx=-1,
      measure_start=measure_nos[0],
      measure_end=measure_nos[-1],
      measure_numbers=[],
      number_of_parts=number_of_parts
    )
    full_score = []

    for l_p in lmxe_paths:
      l = LMXEFile.load(l_p)
      system = l.measures
      full_metadata.measure_numbers.extend(l.metadata.measure_numbers)
      
      full_score.extend(system)
    
    full_metadata.measure_start = full_metadata.measure_numbers[0]
    full_metadata.measure_end = full_metadata.measure_numbers[-1]
    
    full_score_lmxe_path = temp_dir / f'{mscore_id}_full.lmxe'
    LMXEFile.write(full_score_lmxe_path, '\n'.join(full_score), full_metadata)

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
    
    full_score_musicxml = MusicXMLFile.load_musicxml(xml_path)
    part_musicxml_paths = []
    for part in full_score_musicxml.tree.getroot().findall('part'):
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
  parser = get_argument_parser()
  args = parser.parse_args()

  main(Path(args.base_dir))