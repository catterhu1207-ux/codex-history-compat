import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recipe',ROOT/'build_backend.py')
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)

class Profiles(unittest.TestCase):
    def test_missing_pinned_rust_never_installs_a_toolchain(self):
        with tempfile.TemporaryDirectory() as raw:
            target=Path(raw)/'not-created'
            with mock.patch.object(recipe,'checked',side_effect=['synthetic-commit','stable-x86_64-pc-windows-msvc (default)']) as checked, mock.patch.object(recipe.shutil,'which',return_value='synthetic-tool'):
                with self.assertRaisesRegex(ValueError,'no_automatic_install'):
                    recipe.build(None,target,'0.158.0-alpha.2')
            self.assertEqual(checked.call_args_list[-1].args[0],['rustup','toolchain','list'])
            self.assertFalse(target.exists())

    def test_dirty_and_duplicate_application_are_rejected(self):
        profile=recipe.load_profile('0.158.0-alpha.2')[1]
        with mock.patch.object(recipe,'checked',side_effect=[profile['upstream_commit'],' M codex-rs/core/src/lib.rs']):
            with self.assertRaisesRegex(ValueError,'tree_must_be_clean'):
                recipe.apply(Path('.'),'0.158.0-alpha.2')
        with mock.patch.object(recipe,'checked',side_effect=[profile['upstream_commit'],'?? codex-rs/core/src/prompt_history_compat.rs']):
            with self.assertRaisesRegex(ValueError,'tree_must_be_clean'):
                recipe.apply(Path('.'),'0.158.0-alpha.2')

    def test_missing_toolchain_stops_before_checkout(self):
        with tempfile.TemporaryDirectory() as raw:
            target=Path(raw)/'not-created'
            with mock.patch.object(recipe,'checked',return_value='synthetic'), mock.patch.object(recipe.shutil,'which',return_value=None):
                with self.assertRaisesRegex(ValueError,'toolchain_required'):
                    recipe.build(None,target,'0.158.0-alpha.2')
            self.assertFalse(target.exists())

    def test_new_profile_has_exact_source_and_all_file_digests(self):
        folder,profile=recipe.load_profile('0.158.0-alpha.2')
        self.assertEqual(profile['upstream_commit'],'10382da79a2a2d6e8ae221fa63077215389c1ad2')
        self.assertEqual(len(profile['files']),4)
        self.assertEqual(len(json.loads((folder/'migrations.json').read_text())['migrations']),57)

    def test_synthetic_fixture_contains_no_real_paths_or_identifiers(self):
        folder,_=recipe.load_profile('0.158.0-alpha.2')
        fixture=(folder/'deepseek_notice_batch.json').read_text()
        self.assertNotIn('C:\\Users\\',fixture)
        self.assertNotIn('01a0',fixture)

    def test_wrong_commit_and_dirty_tree_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            source=Path(raw)
            subprocess.run(['git','init',str(source)],capture_output=True,check=True)
            (source/'README').write_text('synthetic')
            subprocess.run(['git','-C',str(source),'add','README'],check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','synthetic'],capture_output=True,check=True)
            with self.assertRaisesRegex(ValueError,'upstream_commit_mismatch'):
                recipe.apply(source,'0.158.0-alpha.2')

    def test_legacy_patch_and_entrypoints_remain_present(self):
        self.assertTrue((ROOT/'patches/integration.patch').is_file())
        self.assertIn('b5bffd3ec4db487e7e3dec59663875b0ef7b72ca',(ROOT/'apply.ps1').read_text())
        self.assertIn('b5bffd3ec4db487e7e3dec59663875b0ef7b72ca',(ROOT/'apply.sh').read_text())

if __name__=='__main__':unittest.main()
