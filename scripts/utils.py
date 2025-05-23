import argparse
from datetime import datetime
from pathlib import Path

from modules.svdp.svdp import bbox_utils


get_ts = lambda: datetime.now().strftime('%Y-%m-%d-%H:%M:%S')


def get_argument_parser(args=None):
  parser = argparse.ArgumentParser()

  if args is None:
    args = [
      ('-d', '--base_dir', True, str),
    ]

  for short, full, required, type_ in args:
    parser.add_argument(
      short,
      full,
      required=required,
      type=type_
    )
  
  return parser


def load_bboxs(file_path, merge=True):
  with open(file_path, 'r') as f:
    lines = f.readlines()
  
  bboxs = [ 
    [ int(p) for p in line.strip().split(' ') ] # lx, ly, rx, ry, (height)
    for line in lines
  ]

  if not merge:
    return bboxs

  # sort by y, x
  bboxs = sorted( bboxs, key=lambda x: (x[1], x[0]) )
  
  # merge overlapping bboxs
  bboxs = bbox_utils.merge_match_bboxs(bboxs)

  return bboxs