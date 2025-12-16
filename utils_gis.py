"""
GIS utilities - provides fallback for environments without GDAL/GIS support
"""
from django.db import models as django_models

try:
    from django.contrib.gis.db import models as gis_models
    from django.contrib.gis.geos import Point, GEOSGeometry
    from django.contrib.gis.measure import D
    from django.contrib.gis.db.models.functions import Distance
    USE_GIS = True
except (ImportError, OSError, Exception):
    # Fallback for local development without GDAL
    class MockPointField(django_models.CharField):
        """Mock PointField that stores coordinates as text"""
        def __init__(self, *args, **kwargs):
            # Remove GIS-specific arguments
            kwargs.pop('geography', None)
            kwargs.pop('srid', None)
            kwargs.pop('spatial_index', None)
            kwargs.pop('dim', None)
            # Set max_length for CharField
            kwargs.setdefault('max_length', 255)
            super().__init__(*args, **kwargs)
    
    class MockGISModels:
        """Mock GIS models module for non-GIS environments"""
        PointField = MockPointField
        
        def __getattr__(self, name):
            # For other fields, return regular Django model fields
            return getattr(django_models, name, None)
    
    gis_models = MockGISModels()
    Point = None
    GEOSGeometry = None
    D = None
    Distance = None
    USE_GIS = False

__all__ = ['gis_models', 'Point', 'GEOSGeometry', 'D', 'Distance', 'USE_GIS']
