# Prevent GDAL from being imported
import sys
import os

# Add this directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set GEODJANGO_AVAILABLE to False to prevent GDAL imports
os.environ['GEODJANGO_AVAILABLE'] = 'False'

# Monkey patch Django's geos module to prevent GDAL imports
class DummyGeos:
    def __getattr__(self, name):
        return None

sys.modules['django.contrib.gis.geos'] = DummyGeos()
