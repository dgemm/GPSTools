
# Data from https://www.google.com/settings/takeout

import os
import datetime
import xml.dom.minidom
import zipfile

try:
  import simplejson as json
except ImportError:
  import json


# Files
infile = 'Takeout/Location History/LocationHistory.json'
outfile = 'out.kmz'


MinLineThresh = 0.0025 ** 2
MaxLineThresh = 0.1 ** 2


def parseloc(location):
  result = {
    'lat': 0.0000001*location['latitudeE7'],
    'lng': 0.0000001*location['longitudeE7'],
    'time': 0.001*int(location['timestampMs']),
  }
  
  return result


# Add an endpoint (stop) to the map.
def addEndpoint(doc, PositionsFolder, lat, lng):
  # Add the endpoint
  EndPlacemark = doc.createElement('Placemark')
  PositionsFolder.appendChild(EndPlacemark)
  
  Point = doc.createElement('Point')
  EndPlacemark.appendChild(Point)
  
  extrude = doc.createElement('extrude')
  txt = doc.createTextNode('1')
  extrude.appendChild(txt)
  Point.appendChild(extrude)
  
  altitudeMode = doc.createElement('altitudeMode')
  txt = doc.createTextNode('relativeToGround')
  altitudeMode.appendChild(txt)
  Point.appendChild(altitudeMode)
  
  coordinates = doc.createElement('coordinates')
  txt = doc.createTextNode('%f,%f,0' % (lng, lat))
  coordinates.appendChild(txt)
  Point.appendChild(coordinates)


# Main function
def main():
  # Get current directory
  this_dir = os.path.dirname(os.path.abspath(__file__))
  datafile = os.path.join(this_dir, infile)
  absoutfile = os.path.join(this_dir, outfile)
  
  # Start the KML document
  doc = xml.dom.minidom.Document()
  kml = doc.createElement('kml')
  kml.setAttribute('xmlns', 'http://www.opengis.net/kml/2.2')
  doc.appendChild(kml)
  
  Document = doc.createElement('Document')
  kml.appendChild(Document)
  
  name = doc.createElement('name')
  txt = doc.createTextNode('Track Name')
  name.appendChild(txt)
  Document.appendChild(name)
  
  description = doc.createElement('description')
  txt = doc.createTextNode('Track Description')
  description.appendChild(txt)
  Document.appendChild(description)
  
  PositionsFolder = doc.createElement('Folder')
  PositionsFolder.setAttribute('id', 'Positions')
  Document.appendChild(PositionsFolder)
  
  fopen = doc.createElement('open')
  txt = doc.createTextNode('1')
  fopen.appendChild(txt)
  PositionsFolder.appendChild(fopen)
  
  # Read data file
  with open(datafile, 'r') as f:
    data = json.loads(f.read())
  
  # Make a list of points where we were stopped
  stillstops = []
  
  for item in data['locations']:
    try:
      acts = item['activitys']
    except KeyError:
      acts = None
    except IndexError:
      acts = None
    
    if acts:
      for act in acts:
        for a in act['activities']:
          if (a['type'] == 'still') and (a['confidence'] == 100):
           stillstops.append(parseloc(item))
           break
  
  # Write the stops to XML
  prev_stop = None
  
  for stop in stillstops:
    if not stop:
      continue

    # Enforce minimum distance between stops
    if prev_stop:
      # Squared distance between this point and previous one
      d2 = (stop['lat']-prev_stop['lat'])**2 + (stop['lng']-prev_stop['lng'])**2

      if d2 < MinLineThresh:
        continue
    
    addEndpoint(doc, PositionsFolder, stop['lat'], stop['lng'])
    prev_stop = stop
  
  # Path coordinate pairs
  coordslist = []
  coords = []
  
  prev_point = {
    'lat': 0.0,
    'lng': 0.0,
  }
  
  for item in data['locations']:
    point = parseloc(item)

    # Squared distance between this point and previous
    d2 = (point['lat']-prev_point['lat'])**2 + (point['lng']-prev_point['lng'])**2

    # Distance threshold to start a new line
    if prev_point and (d2 > MaxLineThresh):
      coordslist.append(coords)
      coords = []
    
    # Enforce minimum distance between points
    if prev_point and (d2 < MinLineThresh):
      continue
    
    # Add this point
    coords.append('%f,%f' % (point['lng'], point['lat']))
    prev_point = point
  
  # Add the last set of coords
  coordslist.append(coords)
  coords = []
  
  LinesFolder = doc.createElement('Folder')
  LinesFolder.setAttribute('id', 'Lines')
  Document.appendChild(LinesFolder)
  
  fopen = doc.createElement('open')
  txt = doc.createTextNode('1')
  fopen.appendChild(txt)
  LinesFolder.appendChild(fopen)
  
  Placemark = doc.createElement('Placemark')
  LinesFolder.appendChild(Placemark)
  
  pname = doc.createElement('name')
  txt = doc.createTextNode('GPS Track')
  pname.appendChild(txt)
  Placemark.appendChild(pname)
  
  Style = doc.createElement('Style')
  Placemark.appendChild(Style)
  LineStyle = doc.createElement('LineStyle')
  Style.appendChild(LineStyle)
  color = doc.createElement('color')
  txt = doc.createTextNode('7f00ffff') # Not a real hex code (??)
  color.appendChild(txt)
  LineStyle.appendChild(color)
  width = doc.createElement('width')
  txt = doc.createTextNode('3')
  width.appendChild(txt)
  LineStyle.appendChild(width)
  
  MultiGeometry = doc.createElement('MultiGeometry')
  Placemark.appendChild(MultiGeometry)
  
  for coords in coordslist:
    # Skip single point lines
    if len(coords) < 2:
      continue
    
    LineString = doc.createElement('LineString')
    MultiGeometry.appendChild(LineString)
    
    extrude = doc.createElement('extrude')
    txt = doc.createTextNode('1')
    extrude.appendChild(txt)
    LineString.appendChild(extrude)
    
    tessellate = doc.createElement('tessellate')
    txt = doc.createTextNode('1')
    tessellate.appendChild(txt)
    LineString.appendChild(tessellate)
    
    altitudeMode = doc.createElement('altitudeMode')
    txt = doc.createTextNode('RelativeToGround')
    altitudeMode.appendChild(txt)
    LineString.appendChild(altitudeMode)
    
    coordinates = doc.createElement('coordinates')
    txt = doc.createTextNode(' '.join(coords))
    coordinates.appendChild(txt)
    LineString.appendChild(coordinates)
  
  # Write KMZ file
  with zipfile.ZipFile(absoutfile, 'w', zipfile.ZIP_DEFLATED) as f:
    print
    print 'Writing %s' % outfile
    f.writestr('doc.kml', doc.toprettyxml(encoding='UTF-8'))
  #

# Do the stuff
if __name__ == '__main__':
  main()
  
  if os.name == 'nt':
    os.system('PAUSE')

