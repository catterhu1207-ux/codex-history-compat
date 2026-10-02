import importlib.util,json,subprocess,tempfile,unittest,shutil
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recipe',ROOT/'build_backend.py')
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)

class Profiles(unittest.TestCase):
    def test_4866_profile_is_exact_and_contains_all_73_migrations(self):
        folder, profile = recipe.load_profile('desktop-26.928.4866.0-sqlite-v2')
        self.assertEqual(profile['upstream_commit'], 'ff6aec96948b70d94983af2641a6b67c94faeff5')
        self.assertEqual(profile['version'], '0.159.2')
        self.assertTrue(profile['build_binary_only'])
        self.assertEqual(len(recipe.migration_rows(folder, profile)), 73)
        self.assertEqual(len(profile['source_files']), 6)
        self.assertEqual(profile['official_backend_sha256'], 'fcd5eafefb4ff4a607f244e099e0974f66e17966b6ffda6948de2ef3a7a79530')

    def test_2738_profile_is_independent_and_preserves_compatibility_semantics(self):
        _, previous = recipe.load_profile('0.158.0-alpha.2')
        _, current = recipe.load_profile('desktop-26.924.2738.0')
        self.assertEqual(current['desktop_version'], '26.924.2738.0')
        self.assertEqual(current['version'], '0.158.0-alpha.2.1')
        self.assertEqual(current['official_backend_size'], 321953584)
        self.assertEqual(current['upstream_commit'], '0d9c7cbfa6cf1489f55a8a9542b75ddd2c061807')
        self.assertNotEqual(current['official_backend_sha256'], previous['official_backend_sha256'])
        self.assertEqual(current['files'], previous['files'])
        self.assertEqual(current['source_files'], previous['source_files'])

    def test_corrupted_new_profile_patch_stops_before_application(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            profile='desktop-26.924.2738.0'
            folder=root/'profiles'/profile
            shutil.copytree(ROOT/'profiles'/profile,folder)
            patch=folder/'integration.patch'
            patch.write_bytes(patch.read_bytes()+b'corrupt')
            with mock.patch.object(recipe,'ROOT',root), mock.patch.object(recipe,'checked') as checked:
                with self.assertRaisesRegex(ValueError,'profile_file_identity_mismatch'):
                    recipe.apply(root/'untouched-source',profile)
                checked.assert_not_called()

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
