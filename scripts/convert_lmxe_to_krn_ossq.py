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

import xml.etree.ElementTree as ET

from modules.lmxe.lmxe import linearize_lmxe, delinearize_lmxe
from modules.lmxe.lmxe.Delinearizer import inject_times_to_reduced_lmxe
from modules.lmxe.lmxe.LMXEFile import LMXEFile, LMXEMetadata
from modules.lmxe.lmxe.vocabulary import *
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.symbolic.part_to_score import parts_to_score 
from modules.lmxe.lmxe.symbolic.Pruner import Pruner

from scripts.utils import get_ts, load_ossq_metadata
from scripts.utils.lmxe_integrity import compare_note_sequences

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')


def main(base_dir:Path, reduced:bool=False, verify:bool=True, clean_up:bool=False):
  prj_root = base_dir
  warning_dump = open('./warning.log', 'w')

  errout = prj_root / f'krn_errors_{get_ts()}.log'
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  data = load_ossq_metadata(data_dir / 'scores_w_infos.yaml')
  pbar = list(data.items())
  pbar = tqdm(pbar)
  
  for score_idx, (sqid, body) in enumerate(pbar):
    mscore_id = f'sq{sqid}'
    
    piece_dir = score_dir / body['path']
    lmxe_dir = piece_dir / 'lmxe'

    musicxml_dir = piece_dir / 'musicxml'
    musicxml_dir.mkdir(exist_ok=True)

    krn_dir = piece_dir / 'krn'
    krn_dir.mkdir(exist_ok=True)
    
    if clean_up:
      paths = sorted(musicxml_dir.glob('*.musicxml'))
      paths += sorted(lmxe_dir.glob('*.reconv.lmxe'))
      paths += sorted(krn_dir.glob('*.krn'))
      paths += sorted(krn_dir.glob('*.ekrn'))
      for p in paths:
        p.unlink()
      continue
    
    lmxe_paths = list(sorted(
      lmxe_dir.glob('*.lmxe')
    ))

    for l_p in tqdm(lmxe_paths, leave=False, desc=f"{mscore_id}"):
      lmxe = LMXEFile.load(l_p)

      musicxml_path = musicxml_dir / l_p.with_suffix('.musicxml').name
      if not musicxml_path.exists():
        musicxmlfile = delinearize_lmxe(lmxe)
        musicxmlfile.write(musicxml_path)

      krn_path = krn_dir / l_p.with_suffix('.krn').name
      if not krn_path.exists():
        subprocess.run(
          ["python3", "-m", "converter21", "-f", "musicxml", "-t", "humdrum", str(musicxml_path), str(krn_path)],
          capture_output=True, text=True
        )
      
      if verify:
        reconv_path = musicxml_path.with_suffix('.reconv.musicxml')
        if not reconv_path.exists():
          result = subprocess.run(
            ["python3", "-m", "converter21", "-f", "humdrum", "-t", "musicxml", str(krn_path), str(reconv_path)],
            capture_output=True, text=True
          )

          if not reconv_path.exists():
            with open(errout, 'a') as ef:
              print(f'------ {l_p.stem} ------', file=ef)
              print(f"[ER]: Re-conversion failed", file=ef)
              print('', file=ef)

            continue
        
        pruner = Pruner()
        
        reconv = MusicXMLFile.load_musicxml(reconv_path)
        part_reconv_paths = []
        for p_idx, part in enumerate(reconv.tree.getroot().findall('part')):
          pruner.process_part(part)
          part_reconv_path = musicxml_dir / f'{l_p.stem}_P{p_idx+1}.reconv.musicxml'
          part_reconv = MusicXMLFile(parts_to_score(
            [('multi', part)], 
            measure_numbers=lmxe.metadata.measure_numbers
          ))
          part_reconv.write(part_reconv_path)
          part_reconv_paths.append(part_reconv_path)
        
        musicxml = MusicXMLFile.load_musicxml(musicxml_path)
        part_musicxml_paths = []
        for p_idx, part in enumerate(musicxml.tree.getroot().findall('part')):
          pruner.process_part(part)
          part_musicxml_path = musicxml_dir / f'{l_p.stem}_P{p_idx+1}.musicxml'
          part_musicxml = MusicXMLFile(parts_to_score(
            [('multi', part)], 
            measure_numbers=lmxe.metadata.measure_numbers
          ))
          part_musicxml.write(part_musicxml_path)
          part_musicxml_paths.append(part_musicxml_path)
        
        
        with open(errout, 'a') as ef:
          print(f'------ {l_p.stem} ------', file=ef)
          for i, (orig, delin) in enumerate(zip(part_musicxml_paths, part_reconv_paths)):
            try:
              are_same, msg = compare_note_sequences(orig, delin, tolerance=0.02)
              if not are_same:
                print(f"[ER]: P{i+1}: {msg}", file=ef)
              else:
                print(f"[OK]: P{i+1}: {msg}", file=ef)
            except:
              print(f"[ER]: P{i+1}: Exception occurred during comparison", file=ef)

          print('', file=ef)
        
        # if not l_p.with_suffix('.reconv.lmxe').exists() and reconv_path.exists():
        #   reconv_score_type, reconv_lmxe = linearize_lmxe(
        #     xml=reconv_path,
        #     error_out=warning_dump,
        #     fail_on_unknown_tokens=True,
        #   )
        
        #   for page in reconv_lmxe:
        #     for system in page:
        #       n_parts, measure_nos, times, measures = system
        #       LMXEFile.write(
        #         l_p.with_suffix('.reconv.lmxe'), 
        #         '\n'.join(measures), 
        #         LMXEMetadata(
        #           score_type=reconv_score_type,
        #           dataset=lmxe.metadata.dataset,
        #           score_id=lmxe.metadata.score_id,
        #           page_idx=lmxe.metadata.page_idx,
        #           system_idx=lmxe.metadata.system_idx,
        #           number_of_parts=n_parts,
        #           measure_start=lmxe.metadata.measure_start,
        #           measure_end=lmxe.metadata.measure_end,
        #           measure_numbers=measure_nos,
        #           times=times,
        #         )
        #       )
  
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
  parser.add_argument(
    '-v', '--verify',
    required=False,
    choices=[1, 0],
    default=1,
    type=int
  )
  parser.add_argument(
    '-c', '--clean',
    required=False,
    choices=[1, 0],
    default=0,
    type=int
  )
  
  args = parser.parse_args()

  main(Path(args.base_dir), reduced=bool(args.reduced), verify=bool(args.verify), clean_up=bool(args.clean))