import tempfile,unittest
from pathlib import Path
from test_profiles import recipe

class ModuleHarness(unittest.TestCase):
    def test_unused_external_packages_may_be_pruned_without_upgrading(self):
        a={'package':[{'name':'a','version':'1','source':'registry+fixture','checksum':'same'},
                      {'name':'unused','version':'2','source':'registry+fixture','checksum':'other'}]}
        b={'package':[a['package'][0]]}
        self.assertEqual(recipe.validate_module_harness_lock(a,b),1)

    def test_changed_version_checksum_or_git_source_is_rejected(self):
        entry={'name':'a','version':'1','source':'registry+fixture','checksum':'expected'}
        for field,value in [('version','2'),('checksum','changed'),('source','git+changed#revision')]:
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'external_dependencies_changed'):
                recipe.validate_module_harness_lock({'package':[entry]},{'package':[{**entry,field:value}]})

    def test_unknown_strategy_stops_before_creating_any_files(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);target=root/'not-created'
            with self.assertRaisesRegex(ValueError,'unknown_windows_module_test_strategy'):
                recipe.prepare_windows_module_harness(root,target,{'windows_module_test':'untrusted'},['cargo'],{})
            self.assertFalse(target.exists())

    def test_retained_profiles_keep_their_original_test_strategy(self):
        folder,old=recipe.load_profile('desktop-26.1016.8120.0-sqlite-v2')
        self.assertIsNone(old.get('windows_module_test'))
        self.assertIsNone(recipe.prepare_windows_module_harness(Path('.'),Path('.'),old,['cargo'],{}))
        folder,current=recipe.load_profile('desktop-26.1016.8622.0-sqlite-v2')
        self.assertEqual(current['windows_module_test'],'standalone_real_types_v1')
