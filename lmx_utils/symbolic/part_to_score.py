import xml.etree.ElementTree as ET


def part_to_score(
  part: ET.Element,
  part_id="P2",
  part_name="Piano",
  musicxml_version="3.1"
) -> ET.ElementTree:
  """Embeds a <part> element within a MusicXML <score-partwise> file"""
  
  root = ET.Element("score-partwise")
  root.attrib["version"] = musicxml_version
  
  part_list_element = ET.Element("part-list")
  score_part_element = ET.Element("score-part")
  score_part_element.attrib["id"] = part_id
  part_name_element = ET.Element("part-name")
  part_name_element.text = part_name
  score_part_element.append(part_name_element)
  part_list_element.append(score_part_element)
  
  root.append(part_list_element)
  
  part.attrib["id"] = part_id
  root.append(part)
  
  return ET.ElementTree(root)


def string_quartet_parts_to_score(
  parts:list[ET.Element],
  part_ids:list[str]=['P1', 'P2', 'P3', 'P4'],
  part_names:list[str]=['Violin 1', 'Violin 2', 'Viola', 'Violoncello'],
  musicxml_version="3.1"
) -> ET.ElementTree:
  
  assert len(parts) == 4, "There must be exactly 4 parts for a string quartet."
  
  root = ET.Element("score-partwise")
  root.attrib["version"] = musicxml_version
  
  part_list_element = ET.Element("part-list")
  
  # initialize the part-group element
  part_group_start = ET.Element("part-group")
  part_group_start.attrib["type"] = 'start'
  part_group_start.attrib["number"] = '1'
  
  group_symbol_element = ET.Element("group-symbol")
  group_symbol_element.text = 'bracket'
  
  part_group_start.append(group_symbol_element)
  part_list_element.append(part_group_start)
  
  # add the score-part elements
  for p_id, p_name in zip(part_ids, part_names):
    score_part_element = ET.Element("score-part")
    score_part_element.attrib["id"] = p_id
    part_name_element = ET.Element("part-name")
    part_name_element.text = p_name
    score_part_element.append(part_name_element)
    part_list_element.append(score_part_element)
  
  part_group_end = ET.Element("part-group")
  part_group_end.attrib["type"] = 'end'
  part_group_end.attrib["number"] = '1'
  
  part_list_element.append(part_group_end)
  
  # add score-part element to the root
  root.append(part_list_element)
  
  # add parts to the root
  for p_id, p in zip(part_ids, parts):
    p.attrib["id"] = p_id
    root.append(p)
  
  return ET.ElementTree(root)