
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
    'time': int(location['timestampMs']),
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


# Write KMZ file
def write_kmz(doc, absoutfile):
  with zipfile.ZipFile(absoutfile, 'w', zipfile.ZIP_DEFLATED) as f:
    f.writestr('doc.kml', doc.toxml(encoding='UTF-8'))


def init_new_kmz(outfile):
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
  txt = doc.createTextNode('0')  # Actually used to store a timestamp
  description.appendChild(txt)
  Document.appendChild(description)

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

  # Write a new file
  write_kmz(doc, outfile)


def get_doc_from_kmz(kmzfile):
  with zipfile.ZipFile(kmzfile, 'r') as f:
    kml = f.read('doc.kml')
    doc = xml.dom.minidom.parseString(kml)
    return doc


def get_description_from_doc(doc):
  kml = doc.childNodes[0]
  document = kml.childNodes[0]

  for c1 in document.childNodes:
    if c1.tagName == 'description':
      return c1


def get_timestamp_from_doc(doc):
  description = get_description_from_doc(doc)
  value = description.firstChild.nodeValue

  try:
    return int(value)
  except ValueError:
    return 0


def write_timestamp(doc, latest_timestamp):
  description = get_description_from_doc(doc)
  description.firstChild.nodeValue = str(latest_timestamp)


def get_multigeometry_from_doc(doc):
  kml = doc.childNodes[0]
  document = kml.childNodes[0]

  for c1 in document.childNodes:
    if c1.tagName == 'Folder':
      for c2 in c1.childNodes:
        if c2.tagName == 'Placemark':
          for c3 in c2.childNodes:
            if c3.tagName == 'MultiGeometry':
              return c3


# Main function
def main():
  # Get current directory
  this_dir = os.path.dirname(os.path.abspath(__file__))
  datafile = os.path.join(this_dir, infile)
  absoutfile = os.path.join(this_dir, outfile)

  previous_timestamp = 0

  if os.path.isfile(absoutfile):
    # Try to get saved timestamp from doc
    doc = get_doc_from_kmz(absoutfile)
    previous_timestamp = get_timestamp_from_doc(doc)

    if previous_timestamp > 0:
      print 'Previous timestamp is', previous_timestamp
    else:
      # Unable to find a starting point from the last KMZ
      # Need to start over
      print 'Unable to recover last timestamp from KMZ'
      init_new_kmz(absoutfile)
  else:
    # KMZ doesn't exist at all, start a new one
    init_new_kmz(absoutfile)

  # Open the KMZ for appending
  doc = get_doc_from_kmz(absoutfile)
  MultiGeometry = get_multigeometry_from_doc(doc)

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

  latest_timestamp = previous_timestamp

  for item in get_next_item(f):
    point = parseloc(item)
    timestamp = point['time']

    if timestamp < previous_timestamp:
      print 'Timestamp', timestamp, 'reached previous value', previous_timestamp
      break

    latest_timestamp = max(latest_timestamp, timestamp)

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

  assert latest_timestamp > 0
  write_timestamp(doc, latest_timestamp)

  print
  print 'Writing kmz...'
  write_kmz(doc, absoutfile)

  #

# Do the stuff
if __name__ == '__main__':
  main()

  if os.name == 'nt':
    os.system('PAUSE')

