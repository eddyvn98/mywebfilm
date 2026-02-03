import os
import xml.etree.ElementTree as ET

def parse_nfo(nfo_path):
    """
    Parse TinyMediaManager .nfo file (XML)
    Returns a dictionary of metadata or None if failed.
    """
    if not os.path.exists(nfo_path):
        return None
        
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()
        
        metadata = {
            'title': '',
            'studio': '',
            'genres': [],
            'actors': [],
            'source': 'nfo'
        }
        
        # Extract Title
        title_el = root.find('title')
        if title_el is not None:
            metadata['title'] = title_el.text
            
        # Extract Studio (TMM uses <studio> or <maker> for JAV)
        studio_el = root.find('studio')
        if studio_el is None:
            studio_el = root.find('maker')
            
        if studio_el is not None:
            metadata['studio'] = studio_el.text
            
        # Extract Genres
        for genre_el in root.findall('genre'):
            if genre_el.text:
                metadata['genres'].append(genre_el.text)
                
        # Extract Actors
        for actor_el in root.findall('actor'):
            name_el = actor_el.find('name')
            if name_el is not None and name_el.text:
                metadata['actors'].append(name_el.text)
                
        return metadata
    except Exception as e:
        print(f"Error parsing NFO {nfo_path}: {e}")
        return None

def save_nfo(video_path, metadata):
    """
    Save metadata to .nfo sidecar file (XML format)
    video_path: path to the video file
    metadata: dict {title, actors, studio, genres, code}
    """
    nfo_path = os.path.splitext(video_path)[0] + '.nfo'
    
    root = ET.Element("movie")
    
    title = ET.SubElement(root, "title")
    title.text = metadata.get('title', '')
    
    uniqueid = ET.SubElement(root, "uniqueid", type="num", default="true")
    uniqueid.text = metadata.get('code', '')
    
    studio = ET.SubElement(root, "studio")
    studio.text = metadata.get('studio', '')
    
    maker = ET.SubElement(root, "maker")
    maker.text = metadata.get('studio', '')

    for g in metadata.get('genres', []):
        genre = ET.SubElement(root, "genre")
        genre.text = g
        
    for a in metadata.get('actors', []):
        actor = ET.SubElement(root, "actor")
        name = ET.SubElement(actor, "name")
        name.text = a

    # Add a custom tag for AI verification status
    ai_status = ET.SubElement(root, "ai_verified")
    ai_status.text = "true" if metadata.get('is_ai_verified') else "false"

    tree = ET.ElementTree(root)
    
    # Use indent if possible (minidom formatting)
    try:
        from xml.dom import minidom
        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(xmlstr)
    except:
        tree.write(nfo_path, encoding="utf-8", xml_declaration=True)
        
    print(f"  [NFO] Saved sidecar: {nfo_path}")
    return True
