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


def main(base_dir:Path, verify:bool=True):
  prj_root = base_dir

  errout = prj_root / f'clean_musicxml_errors_{get_ts()}.log'
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  data = load_ossq_metadata(data_dir / 'scores_w_infos.yaml')
  pbar = list(data.items())
  pbar = tqdm(pbar)
  for score_idx, (sqid, body) in enumerate(pbar):
    mscore_id = f'sq{sqid}'
    pbar.set_description(mscore_id)

    xml_dir = score_dir / body['path']

    temp_dir = xml_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)

    general_pruner = Pruner( prune_prints=False )

    xml_path = xml_dir / f'{mscore_id}.musicxml'
    xml = MusicXMLFile.load_musicxml(xml_path)

    # save uncleaned MusicXML for comparison
    part_musicxml_paths = []
    for part in xml.tree.getroot().findall('part'):
      part_musicxml_path = temp_dir / f'{mscore_id}_{part.get("id")}.musicxml'
      
      # if part_musicxml_path.exists():
      #   part_musicxml_paths.append(part_musicxml_path)
      #   continue
      
      # do not prune for now
      general_pruner.process_part(part)
      part_musicxml = MusicXMLFile(parts_to_score([('multi', part)]))
      part_musicxml.write(part_musicxml_path)
      part_musicxml_paths.append(part_musicxml_path)
    
    # load un-pruned MusicXML again
    xml = MusicXMLFile.load_musicxml(xml_path)
    # prune barlines
    barline_pruner = Pruner( 
        prune_barlines=True,
        prune_prints=False,
        prune_directions=False,
        prune_harmony=False,
        prune_slur_numbering=False,
      )
    for part in xml.tree.getroot().findall('part'):
      barline_pruner.process_part(part)
    # clean MusicXML
    xml.remove_dangling_backup_sequences()
    for part in xml.tree.getroot().findall('part'):
      general_pruner.process_part(part)
    
    # save cleaned MusicXML for full score
    xml.write(xml_dir / f'{mscore_id}_cleaned.musicxml')

    # save cleaned MusicXML parts
    cleaned_part_musicxml_paths = []
    for part in xml.tree.getroot().findall('part'):
      part_musicxml_path = temp_dir / f'{mscore_id}_{part.get("id")}_cleaned.musicxml'
      part_musicxml = MusicXMLFile(parts_to_score([('multi', part)]))
      part_musicxml.write(part_musicxml_path)
      cleaned_part_musicxml_paths.append(part_musicxml_path)
    
    with open(errout, 'a') as errout_f:
      print(f'------ {mscore_id} ------', file=errout_f)
      for i, (orig, delin) in enumerate(zip(part_musicxml_paths, cleaned_part_musicxml_paths)):
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
    '-v', '--verify',
    required=False,
    choices=[1, 0],
    default=1,
    type=int
  )
  
  
  args = parser.parse_args()

  main(Path(args.base_dir), verify=bool(args.verify))