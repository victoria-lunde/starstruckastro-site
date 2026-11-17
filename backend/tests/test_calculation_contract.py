"""Deterministic adapter tests; these do not validate astronomical accuracy."""
import unittest
from chart_engine import calculate, ChartError

class FakeSwiss:
    FLG_SWIEPH=2
    FLG_SPEED=256
    FLG_SIDEREAL=65536
    SIDM_LAHIRI=1
    AST_OFFSET=10000
    SUN=0
    MOON=1
    ECL2HOR=0
    version='test-double'
    def set_ephe_path(self,path):pass
    def set_sid_mode(self,mode):pass
    def julday(self,y,m,d,h):return 2451545+h/24
    def houses_ex(self,*args):return tuple(i*30 for i in range(12)),(18,278)
    def calc_ut(self,t,ident,flags):
        if ident>=10000:raise ValueError('Missing asteroid file')
        return (ident*30+2,0,1,-1 if ident==4 else 1,0,0),flags
    def fixstar2_ut(self,*args):raise ValueError('Missing catalog')
    def azalt(self,*args):return (0,20,20)

class CalculationContract(unittest.TestCase):
    def payload(self,**changes):
        return dict(dict(date='2000-01-01',time='12:00',timezone='Etc/UTC',
                    latitude=0,longitude=0,points=[]),**changes)
    def test_known_time_and_missing_optional_data(self):
        c=calculate(self.payload(points=['Medusa','Algol','Part of Fortune']),FakeSwiss(),'/unused')
        self.assertEqual(c['angles']['rising']['degree'],18)
        self.assertEqual(len(c['cusps']),12)
        self.assertTrue(c['bodies']['Mars']['retrograde'])
        self.assertEqual(c['bodies']['Part of Fortune']['longitude'],48)
        self.assertEqual([p['name'] for p in c['unavailable']],['Medusa','Algol'])
    def test_unknown_omits_time_sensitive_results(self):
        c=calculate(self.payload(unknown_time=True),FakeSwiss(),'/unused')
        self.assertIsNone(c['angles'])
        self.assertEqual(c['cusps'],[])
        self.assertEqual(c['aspects'],[])
        self.assertTrue(all(p['house'] is None for p in c['bodies'].values()))
        self.assertEqual(len(c['moon_day_range']),2)
    def test_approximation_fallback_rejected(self):
        class Fallback(FakeSwiss):
            def calc_ut(self,*args):return (0,0,0,0,0,0),0
        with self.assertRaises(ChartError) as ctx:
            calculate(self.payload(),Fallback(),'/unused')
        self.assertEqual(ctx.exception.code,'ephemeris_unavailable')

if __name__=='__main__':unittest.main()
