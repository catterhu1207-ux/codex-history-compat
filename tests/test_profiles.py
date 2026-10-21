import importlib.util,json,subprocess,tempfile,unittest,shutil
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recipe',ROOT/'build_backend.py')
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)

class Profiles(unittest.TestCase):
    def test_version_injection_binds_release_tags_and_preserves_external_packages(self):
        for old in ('0.0.0', '0.163.0-alpha.11'):
            manifest='[workspace.package]\nversion = "'+old+'"\n'
            lock='[[package]]\nname = "codex-core"\nversion = "'+old+'"\n[[package]]\nname = "external"\nversion = "1.0.0"\nsource = "registry+fixture"\n'
            data={'version':'0.163.0-alpha.11.1','upstream_version':old}
            changed,changed_lock=recipe.inject_workspace_version(manifest,lock,data)
            self.assertIn('version = "0.163.0-alpha.11.1"',changed)
            self.assertIn('version = "1.0.0"',changed_lock)
            with self.assertRaisesRegex(ValueError,'upstream_workspace_version_mismatch'):
                recipe.inject_workspace_version(manifest,lock,{**data,'upstream_version':'wrong'})
            with self.assertRaisesRegex(ValueError,'external_dependencies_changed'):
                recipe.inject_workspace_version(manifest,lock.replace('version = "1.0.0"','version = "'+old+'"'),data)

    def test_6573_profile_binds_new_upstream_and_preserves_migrations(self):
        folder, current = recipe.load_profile('desktop-26.1016.6573.0-sqlite-v2')
        previous_folder, previous = recipe.load_profile('desktop-26.1013.4894.0-sqlite-v2')
        self.assertNotEqual(current['upstream_commit'], previous['upstream_commit'])
        self.assertEqual(current['upstream_commit'], '5425d3e625daa58eea3ad1de27c087eb3b2ffbd3')
        self.assertEqual(current['version'], '0.163.0-alpha.11.1')
        self.assertEqual(current['source_files'], previous['source_files'])
        self.assertEqual(recipe.migration_rows(folder, current), recipe.migration_rows(previous_folder, previous))
        inventory = json.loads((folder / current['sqlite_migrations']).read_text())
        self.assertEqual(inventory['upstream_commit'], current['upstream_commit'])
        self.assertEqual(inventory['official_backend_sha256'], current['official_backend_sha256'])
        self.assertEqual(current['official_backend_equivalence']['upstream_release_commit'], current['upstream_commit'])

    def test_4894_profile_reuses_identical_unsigned_backend_code(self):
        new_folder, current = recipe.load_profile('desktop-26.1013.4894.0-sqlite-v2')
        old_folder, previous = recipe.load_profile('desktop-26.1013.3656.0-sqlite-v2')
        self.assertEqual(current['id'], 'desktop-26.1013.4894.0-sqlite-v2')
        self.assertEqual(current['desktop_version'], '26.1013.4894.0')
        self.assertEqual(current['official_backend_sha256'], 'f6dbf48cb70f62649c645f26c87dc9bf84cc36986202dfad8e12fb5b8ca70312')
        self.assertEqual(current['official_backend_size'], previous['official_backend_size'])
        self.assertEqual(current['upstream_commit'], previous['upstream_commit'])
        self.assertEqual(current['version'], previous['version'])
        self.assertEqual({k:v for k,v in current['files'].items() if k!='sqlite-migrations.json'},
                         {k:v for k,v in previous['files'].items() if k!='sqlite-migrations.json'})
        self.assertNotEqual(current['files']['sqlite-migrations.json'], previous['files']['sqlite-migrations.json'])
        self.assertEqual(current['source_files'], previous['source_files'])
        self.assertEqual(recipe.migration_rows(new_folder, current), recipe.migration_rows(old_folder, previous))
        with self.assertRaisesRegex(ValueError, 'migration_official_backend_identity_mismatch'):
            recipe.migration_rows(new_folder, {**current, 'official_backend_sha256': previous['official_backend_sha256']})
        equivalence = current['official_backend_equivalence']
        self.assertEqual(equivalence['predecessor_backend_sha256'], previous['official_backend_sha256'])
        self.assertTrue(equivalence['all_named_sections_identical'])
        self.assertEqual(equivalence['unsigned_body_sha256_with_zero_checksum'],
                         '27647acf46ec1107fb2f052258a92750f9229218fcc0b8595ed337c53d1c6dea')

    def test_3656_profile_extends_exact_9446_migration_lineage(self):
        folder, current = recipe.load_profile('desktop-26.1013.3656.0-sqlite-v2')
        old_folder, previous = recipe.load_profile('desktop-26.1007.9446.0-sqlite-v2')
        rows = recipe.migration_rows(folder, current)
        old_rows = recipe.migration_rows(old_folder, previous)
        old_by_path = {row['path']: row for row in old_rows}
        current_by_path = {row['path']: row for row in rows}
        self.assertEqual(current['upstream_commit'], '4ebc485ca321243727539187169425fcf972f2c4')
        self.assertEqual(current['version'], '0.163.0-alpha.10.2')
        self.assertEqual(current['official_backend_sha256'], '9ecb9df2ecafcc00542ef0966c6f1737a81397dc9531b0a4b178238e2bf4a46d')
        self.assertEqual(len(rows), 77)
        self.assertEqual(len({row['database'] for row in rows}), 6)
        self.assertEqual(set(current_by_path) - set(old_by_path), {
            'codex-rs/state/migrations/0060_guardian_review_feedback.sql',
            'codex-rs/state/migrations/0061_thread_read_state.sql',
        })
        self.assertTrue(all(current_by_path[path] == old for path, old in old_by_path.items()))
        self.assertEqual(len(current['source_files']), 7)
        self.assertNotEqual(current['id'], previous['id'])
        self.assertNotEqual(current['official_backend_sha256'], previous['official_backend_sha256'])

    def test_9446_profile_binds_exact_source_and_75_migrations(self):
        folder, profile = recipe.load_profile('desktop-26.1007.9446.0-sqlite-v2')
        self.assertEqual(profile['upstream_commit'], '740e5af33c71225640e0c1c1555c514c2c93ab74')
        self.assertEqual(profile['version'], '0.162.0-alpha.17.2')
        rows=recipe.migration_rows(folder,profile)
        self.assertEqual(len(rows),75)
        self.assertEqual(len({row['source_path'] for row in rows}),75)
        self.assertEqual(len({row['database'] for row in rows}),6)
        self.assertEqual(profile['official_backend_sha256'],'e98c516f1c8935789aabe9122ee7e05ec4c3efd1ba6acf179242e031c495b99e')
        self.assertEqual(len(profile['source_files']),7)
        self.assertNotIn('Cargo.lock',(folder/'integration.patch').read_text())

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
