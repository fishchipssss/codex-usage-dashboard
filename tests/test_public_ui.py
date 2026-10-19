"""Portable UI contracts; no personal paths or local backup dependencies."""
import re
import unittest
import test_codex_usage_dashboard as existing

HTML = existing.dashboard.HTML

class PublicUIContracts(unittest.TestCase):
    def test_both_appearances_and_reduced_motion(self):
        for contract in ['data-theme="dark"', 'prefers-reduced-motion', 'color-scheme:dark', 'themeSelect']:
            self.assertIn(contract, HTML)

    def test_primary_total_and_subset_semantics(self):
        start=HTML.index('    function renderMetrics()')
        end=HTML.index('    function renderTable()',start)
        metrics=HTML[start:end]
        self.assertIn('const summary = summarizeFilteredSessions();',metrics)
        for label in ['totalOverview','subsetInput','subsetOutput','apiEquivalent']:
            self.assertIn(label,metrics)
        self.assertLess(metrics.index("metric(t('totalOverview')"),metrics.index("metric(t('metricInput')"))

    def test_accessible_navigation_and_dialog(self):
        for contract in ['class="skip-link"','aria-sort','aria-pressed',"event.key !== 'Tab'","event.key === 'Escape'","document.getElementById('dashboardMain').inert"]:
            self.assertIn(contract,HTML)

    def test_ui_uses_only_local_assets(self):
        self.assertFalse(re.findall(r'<(?:script|link|img)[^>]+(?:src|href)="https?://',HTML))

    def test_source_provenance_and_keyboard_chart(self):
        for contract in ['sourceStatusBody','provenance-disclosure','curveTooltip','canvas.onkeydown','Contributing files','Models · event tokens']:
            self.assertIn(contract,HTML)

    def test_responsive_layout_and_empty_selection(self):
        for contract in ['max-width:1279px','max-width:700px','min-width:850px','if (!selectionVisible) clearDetails();','captureListFocus']:
            self.assertIn(contract,HTML)

if __name__=='__main__':
    unittest.main()
