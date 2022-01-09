import unittest
import src.agarnt.action as act

class TestAction(unittest.TestCase):
    
    def test_encode_simple_action(self):
        down = act.AgarntAction.D
        expected_D = {"directions":{"L":False, "D":True, "R":False, "U":False}}
        
        self.assertEqual(down.encode(), expected_D)
        
    def test_encode_complex_action(self):
        left_up = act.AgarntAction.LU
        expected_LU = {"directions":{"L":True, "D":False, "R":False, "U":True}}
        
        self.assertEqual(left_up.encode(), expected_LU)
        
    
    def test_decode_simple_action(self):
        expected_D = act.AgarntAction.D
        down = {"directions":{"L":False, "D":True, "R":False, "U":False}}
        
        self.assertEqual(act.AgarntAction.decode(down), expected_D)
        
    def test_decode_complex_action(self):
        expected_LU = act.AgarntAction.LU
        left_up = {"directions":{"L":True, "D":False, "R":False, "U":True}}
        
        self.assertEqual(act.AgarntAction.decode(left_up), expected_LU)
        
    def test_get_all(self):
        expected = [act.AgarntAction.L, act.AgarntAction.D, act.AgarntAction.R, act.AgarntAction.U,
                    act.AgarntAction.LD, act.AgarntAction.LU, act.AgarntAction.RD, act.AgarntAction.RU]
        
        self.assertListEqual(act.AgarntAction.get_all(), expected)