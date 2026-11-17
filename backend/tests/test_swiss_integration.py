"""Requires actual ephemeris data. Broad J2000 astronomy sanity check only."""
import os
import unittest
from chart_engine import calculate
try:import swisseph as swe
except ImportError:swe=None

@unittest.skipUnless(swe and os.getenv('EPHEMERIS_PATH'),'Swiss Ephemeris and provisioned data required')
class SwissIntegration(unittest.TestCase):
    def test_j2000_sun_and_unknown_time(self):
        chart=calculate({'date':'2000-01-01','time':'12:00','timezone':'Etc/UTC','latitude':0,'longitude':0,'points':[],'unknown_time':True},swe,os.environ['EPHEMERIS_PATH'])
        self.assertAlmostEqual(chart['bodies']['Sun']['longitude'],280.37,delta=0.1)
        self.assertIsNone(chart['angles'])
        self.assertTrue(all(p['house'] is None for p in chart['bodies'].values()))
        self.assertEqual(len(chart['moon_day_range']),2)
