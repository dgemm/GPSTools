
# Data from https://www.google.com/settings/takeout

import os
import datetime
import xml.dom.minidom
import zipfile

try:
  import simplejson as json
except ImportError:
  print 'Using the slow json parser'
  import json


# Files
infile = 'Takeout/Location History/Location History.json'
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


class LocationDataFile(object):
  def __init__(self, fname):
    self.f = open(infile, 'rb')
    self.f.seek(0, 2)
    self.f_size = self.f.tell()
    self.rewind()

  def rewind(self):
    self.f.seek(1)  # Past the root level "{" character
    self.bytes_read = 0
    self.progress = 0

  def print_progress(self):
    progress = int(100*float(self.bytes_read)/self.f_size)

    if progress != self.progress:
      print '%d%%' % progress
      self.progress = progress

  def getchar(self):
    self.bytes_read += 1
    return self.f.read(1)


def get_next_item(f):
  chunk = ''
  curlies = 0

  while True:
    c = f.getchar()

    if not c:
      raise StopIteration

    if len(chunk) == 0 and c != '{':
      # Skip until the first "{"
      continue

    # Count opening and closing curlies to find the end of object
    if c == '{':
      curlies += 1
    elif c == '}':
      curlies -= 1

    chunk += c

    if curlies == 0:
      f.print_progress()

      yield json.loads(chunk)

      # Reset chunk
      chunk = ''
      curlies = 0
  #










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






  # Open data file
  f = LocationDataFile(datafile)








  # Path coordinate pairs
  coordslist = []
  coords = []

  prev_point = {
    'lat': 0.0,
    'lng': 0.0,
  }

  print 'Finding points'
  f.rewind()

  for item in get_next_item(f):
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

