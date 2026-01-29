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
