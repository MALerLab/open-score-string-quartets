from pathlib import Path
import subprocess
from tqdm.auto import tqdm

from scripts.utils import get_argument_parser


def main(base_dir:Path):
  pi_dataset_dir = Path.home() / 'userdata' / 'olimpic_dataset' / 'grandstaff-lmx'

  pi_kern = pi_dataset_dir.glob('**/*.krn')
  pi_kern = list(sorted(pi_kern))

  for kern in tqdm(pi_kern):
    path_parts = list(kern.parts)
    out_path = Path('/') / '/'.join(path_parts[1:4])
    out_path /= 'olimpic_dataset_yolo'
    out_path /= '/'.join(path_parts[5:])
    out_path = out_path.with_suffix('.musicxml')

    subprocess.run(["python3", "-m", "converter21", "-f", "humdrum", "-t", "musicxml", str(kern), str(out_path)])


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(Path(args.base_dir))