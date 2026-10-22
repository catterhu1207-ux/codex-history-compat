import importlib.util,json,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cache_recipe',ROOT/'build_backend.py')
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)

class ModuleTestCache(unittest.TestCase):
    def test_completed_tests_can_resume_after_compiler_cache_retirement(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp);binding={'source':'fixed','recipe':'fixed','toolchain':'fixed','migration':{'one':'hash'}}
            (target/'test.log').write_text('test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 20 filtered out\n')
            self.assertIsNone(recipe.cached_module_test(target,binding))
            proof=recipe.save_module_test(target,binding)
            self.assertEqual(recipe.cached_module_test(target,binding),proof)
            self.assertEqual(proof['test_count'],15)
            for key in binding:
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'inputs_changed'):
                    recipe.cached_module_test(target,{**binding,key:'changed'})
            (target/'test.log').write_text('test result: ok. 14 passed; 0 failed; 0 ignored;\n')
            with self.assertRaisesRegex(ValueError,'log_changed'):recipe.cached_module_test(target,binding)

    def test_interrupted_failed_ignored_and_duplicate_logs_cannot_be_cached(self):
        for text in ('Compiling codex-core\n','test result: FAILED. 14 passed; 1 failed; 0 ignored;\n',
                'test result: ok. 0 passed; 0 failed; 0 ignored;\n','test result: ok. 14 passed; 0 failed; 1 ignored;\n',
                'test result: ok. 15 passed; 0 failed; 0 ignored;\n'*2):
            with self.subTest(text=text),tempfile.TemporaryDirectory() as temp:
                target=Path(temp);(target/'test.log').write_text(text)
                with self.assertRaisesRegex(ValueError,'no_complete_success'):recipe.save_module_test(target,{'fixed':'inputs'})
                self.assertFalse((target/'module-test-cache.json').exists())

    def test_stale_or_missing_log_and_nonpassed_receipts_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp);(target/'test.log').write_text('test result: ok. 15 passed; 0 failed; 0 ignored;\n')
            recipe.save_module_test(target,{'fixed':'inputs'});path=target/'module-test-cache.json';v=json.loads(path.read_text());v['status']='running';path.write_text(json.dumps(v))
            with self.assertRaisesRegex(ValueError,'inputs_changed'):recipe.cached_module_test(target,{'fixed':'inputs'})
            (target/'test.log').unlink()
            with self.assertRaisesRegex(ValueError,'files_invalid'):recipe.cached_module_test(target,{'fixed':'inputs'})
