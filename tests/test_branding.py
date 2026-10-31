from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class BrandingTests(unittest.TestCase):
    def test_brand_assets_and_names(self):
        html=(ROOT/'web/index.html').read_text(encoding='utf-8')
        spec=(ROOT/'FORGE.spec').read_text(encoding='utf-8')
        self.assertIn('Fluxo RIP | Central de Produção',html)
        self.assertIn('brand-fluxorip.css',html)
        self.assertIn('brand-fluxorip.js',html)
        self.assertIn('fluxo-rip-mark.svg',html)
        self.assertIn('name=\'FluxoRIP\'',spec)
        self.assertIn('FluxoRIP.ico',spec)
        self.assertTrue((ROOT/'FluxoRIP.ico').exists())

    def test_source_colors_and_motion(self):
        css=(ROOT/'web/brand-fluxorip.css').read_text(encoding='utf-8')
        svg=(ROOT/'web/assets/fluxo-rip-mark.svg').read_text(encoding='utf-8')
        for color in ('#00A6D6','#E5007D','#FFD500'):
            self.assertIn(color,svg)
        self.assertIn('prefers-reduced-motion:reduce',css)
        self.assertIn('brand-layer-m',css)
        self.assertIn('brand-splash',css)

    def test_launcher_preserves_legacy_data(self):
        paths=(ROOT/'app/paths.py').read_text(encoding='utf-8')
        self.assertIn("/ 'FORGE'",paths)
        spec=(ROOT/'FORGE.spec').read_text(encoding='utf-8')
        self.assertIn("'forge_launcher.py'",spec)

if __name__=='__main__':
    unittest.main()
