from pathlib import Path
import subprocess
from tqdm.auto import tqdm

from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile

from scripts.utils import get_argument_parser


def main(base_dir:Path):
  pi_dataset_dir = Path.home() / 'userdata' / 'olimpic_dataset_yolo' / 'grandstaff-lmx'

  pi_musicxml = pi_dataset_dir.glob('**/*.musicxml')
  pi_musicxml = list(sorted(pi_musicxml))

  for musicxml_path in tqdm(pi_musicxml):
    musicxml_file = MusicXMLFile.load_musicxml(musicxml_path)

    el_partwise = musicxml_file.tree.getroot()
    title = el_partwise.find('movement-title')
    identification = el_partwise.find('identification')
    part_list = el_partwise.find('part-list')

    old_part_id = str(part_list.find('score-part').attrib['id'])
    if old_part_id == 'P2':
      continue
    
    part_list.find('score-part').attrib['id'] = 'P2'
    part_list.find('score-part').find('part-name').text = 'Piano'

    tgt_part = [p for p in el_partwise.findall('part') if p.attrib['id'] == old_part_id][0]
    tgt_part.attrib['id'] = 'P2'

    for i, m in enumerate(tgt_part.findall('measure')):
      i += 1
      m.attrib['number'] = str(i)
    
    # re-number voices in staff 2
    # voice numbers in staff 2 starts from 5
    voices = set(sorted([
      note.find('voice').text 
      for note in el_partwise.findall(".//note[staff='2']") 
      if note.find('voice') is not None
    ]))
    
    voices = {
      v: str(i + 5)
      for i, v in enumerate(voices)
    }
    
    for i, n in enumerate(el_partwise.findall(".//note[staff='2']")):
      voice = n.find('voice')
      if voice is not None:
        voice.text = voices.get(voice.text, voice.text)

    if title is not None:
      el_partwise.remove(title)
    if identification is not None:
      el_partwise.remove(identification)
    
    musicxml_file.write(musicxml_path)



if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(Path(args.base_dir))