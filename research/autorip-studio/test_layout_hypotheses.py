import hashlib, os, struct, tempfile, unittest
from pathlib import Path
from layout_hypotheses import inspect,offsets

class TestLayout(unittest.TestCase):
 def make(self,rows=2,stride=3,slots=12,signature=0x5555,extra=b''):
  f=tempfile.NamedTemporaryFile(delete=False)
  f.write(struct.pack('<12I',signature,0,0,rows,stride,0,0,slots,0,0,0,0))
  f.write(bytes([3])*rows*stride*slots+extra);f.close();self.addCleanup(lambda:os.unlink(f.name));return f.name
 def test_valid(self):
  p=self.make();d=inspect(p);self.assertTrue(d['geometry_matches']);self.assertFalse(d['layout_discriminated'])
 def test_hash(self):
  p=self.make();self.assertEqual(inspect(p)['sha256'],hashlib.sha256(Path(p).read_bytes()).hexdigest())
 def test_bad_signature(self):
  with self.assertRaisesRegex(ValueError,'signature'):inspect(self.make(signature=1))
 def test_trailing_bytes(self):
  with self.assertRaisesRegex(ValueError,'size mismatch'):inspect(self.make(extra=b'x'))
 def test_truncated(self):
  p=self.make();Path(p).write_bytes(b'abc')
  with self.assertRaisesRegex(ValueError,'truncated'):inspect(p)
 def test_zero_rows(self):
  with self.assertRaisesRegex(ValueError,'zero geometry'):inspect(self.make(rows=0))
 def test_row_major_offsets(self):
  self.assertEqual(offsets(3,12,5,1,2)[0],48+(1*12+2)*5)
 def test_plane_major_offsets(self):
  self.assertEqual(offsets(3,12,5,1,2)[1],48+(2*3+1)*5)
 def test_layouts_differ(self):
  a,b=offsets(3,12,5,1,2);self.assertNotEqual(a,b)
 def test_out_of_range(self):
  with self.assertRaises(IndexError):offsets(3,12,5,3,0)
 def test_same_origin(self):
  self.assertEqual(offsets(3,12,5,0,0),(48,48))

if __name__=='__main__':unittest.main()
