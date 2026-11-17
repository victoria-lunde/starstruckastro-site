import unittest
from datetime import timedelta
from chart_engine import local_to_utc, ChartError, placement, aspects, validate

class EngineTests(unittest.TestCase):
    def test_historical_dst(self):
        self.assertEqual(local_to_utc('1992-04-18','05:35','America/Los_Angeles').isoformat(),'1992-04-18T12:35:00+00:00')
    def test_gap(self):
        with self.assertRaises(ChartError) as ctx:local_to_utc('2024-03-10','02:30','America/Chicago')
        self.assertEqual(ctx.exception.code,'nonexistent_local_time')
    def test_fold(self):
        with self.assertRaises(ChartError):local_to_utc('2024-11-03','01:30','America/Chicago')
        first=local_to_utc('2024-11-03','01:30','America/Chicago',0)
        second=local_to_utc('2024-11-03','01:30','America/Chicago',1)
        self.assertEqual(second-first,timedelta(hours=1))
    def test_no_dst(self):
        self.assertEqual(local_to_utc('2000-01-01','12:00','Asia/Kolkata').hour,6)
    def test_wrap_and_house(self):
        self.assertEqual(placement(360)['sign'],'Aries')
        self.assertEqual(placement(-1)['sign'],'Pisces')
        self.assertEqual(placement(0,rising=359)['house'],2)
        self.assertIsNone(placement(23)['house'])
    def test_aspect_wrap(self):
        result=aspects({'Sun':placement(359),'Moon':placement(1)})
        self.assertEqual(result[0]['orb'],2)
        self.assertEqual(result[0]['aspect'],'conjunction')
    def test_bad_coordinates(self):
        for val in [float('nan'),float('inf'),91]:
            with self.assertRaises(ChartError):validate({'date':'2000-01-01','latitude':val,'longitude':0})
    def test_bad_body(self):
        with self.assertRaises(ChartError):validate({'date':'2000-01-01','latitude':0,'longitude':0,'points':['made up']})
    def test_shadow_options(self):
        p={'date':'2000-01-01','latitude':0,'longitude':0,'points':['Algol','Medusa','Nemesis','Nessus','Dejanira','Apophis']}
        self.assertEqual(len(validate(p)[2]),6)
    def test_clock_must_be_local(self):
        with self.assertRaises(ChartError):
            local_to_utc('2000-01-01','12:00+03:00','America/Chicago')
    def test_invalid_payload_types(self):
        for payload in [None, [], 'chart', {'date':'2000-01-01','latitude':True,'longitude':0}]:
            with self.assertRaises(ChartError):validate(payload)
if __name__=='__main__':unittest.main()
