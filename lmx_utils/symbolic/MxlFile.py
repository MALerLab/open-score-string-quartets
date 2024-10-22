import zipfile
import xml.etree.ElementTree as ET


class MxlFile:
  """Loads and lets you manipulate a MusicXML file"""

  def __init__(self, tree: ET.ElementTree):
    self.tree = tree

    # all MuseScore exported MusicXML files should be partwise organized
    # https://www.w3.org/2021/06/musicxml40/tutorial/structure-of-musicxml-files/
    assert tree.getroot().tag == "score-partwise"
  
  
  @staticmethod
  def load_mxl(path: str) -> "MxlFile":
    """Loads MusicXML from the compressed MXL file"""
    with zipfile.ZipFile(path, "r") as archive:
      for record in archive.infolist():
        if record.filename.startswith("META-INF"):
          continue
        if record.filename.endswith(".xml"):
          inner_file_name = record.filename
          break
      with archive.open(inner_file_name) as file:
        tree = ET.parse(file)
        return MxlFile(tree)
  
  
  def resolve_piano_part_id(self) -> str:
    """Resolves the ID of the piano part, e.g. 'P2'"""
    part_list = self.tree.getroot().find("part-list")
    
    for part in part_list.findall("score-part"):
      if part.find("score-instrument/instrument-name").text in [
        "Piano", "Grand Piano", "Acoustic Grand Piano",
        "Harpsichord", "Pianoforte", "Piano (2)"
      ]:
        return part.attrib["id"]
      if part.find("part-name").text in [
        "Pianoforte"
      ]:
        return part.attrib["id"]
    
    raise Exception(
      "No piano part found:\n" \
        + str(ET.tostring(part_list), "utf-8")
    )
  
  
  def get_piano_part(self) -> ET.Element:
    """Returns the <part> element of the piano, containing measures."""
    part_id = self.resolve_piano_part_id()

    parts = [
      part for part in self.tree.findall("part")
      if part.attrib["id"] == part_id
    ]
    assert len(parts) == 1
    part = parts[0]

    return part
  
  
  def resolve_string_part_ids(self) -> list[str]:
    """Resolves the list of IDs of the strings parts, e.g. [P1, P2, P3, P4]"""
    part_list = self.tree.getroot().find("part-list")
    
    string_part_ids = []
    
    for part in part_list.findall("score-part"):
      if (
        part.find("score-instrument/instrument-name").text in { "Violin", "Viola", "Cello", "Violoncello" } or
        part.find("part-name").text in { "Violin 1", "Violin 2", "Viola", "Cello", "Violoncello" }
      ):
        string_part_ids.append(part.attrib["id"])
    
    assert len(string_part_ids) > 0, "No string parts found."
    
    if len(string_part_ids) > 4:
      print("Warning: More than 4 string parts found. Using the first 4.")
      string_part_ids = string_part_ids[:4]
    
    return string_part_ids
  
  
  def get_string_quartet_parts(self) -> list[ET.Element]:
    """Returns the <part> elements of the string quartet, containing measures."""
    string_part_ids = self.resolve_string_part_ids()
    
    parts = [
      part for part in self.tree.findall("part")
      if part.attrib["id"] in string_part_ids
    ]
    
    assert len(parts) == 4
    return parts